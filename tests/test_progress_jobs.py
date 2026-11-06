"""Progress reservations, independent replay, terminal states, and expiry."""

import json
from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.sse import progress_generator, send_progress_update
from app.main import app
from app.services import jobs


@pytest.fixture(autouse=True)
def isolate_jobs() -> Iterator[None]:
    jobs._jobs.clear()
    yield
    jobs._jobs.clear()


@pytest.mark.asyncio
async def test_two_subscribers_receive_replay_and_same_terminal_event() -> None:
    job = jobs.create_job()
    jobs.claim_job(job.job_id)
    await send_progress_update(job.job_id, 0.3, "Computing", "inference")
    first = progress_generator(job.job_id, after=2)
    second = progress_generator(job.job_id, after=2)
    assert json.loads((await anext(first))["data"])["message"] == "Computing"
    assert json.loads((await anext(second))["data"])["message"] == "Computing"
    assert len(job.subscribers) == 2
    jobs.finish_job(job, "failed", "Failed safely")
    assert (await anext(first))["event"] == "failed"
    assert (await anext(second))["event"] == "failed"
    await first.aclose()
    await second.aclose()
    assert not job.subscribers
    assert jobs.get_job(job.job_id).status == "failed"


@pytest.mark.asyncio
async def test_disconnect_does_not_delete_job_and_reconnect_replays() -> None:
    job = jobs.create_job()
    first = progress_generator(job.job_id)
    event = await anext(first)
    await first.aclose()
    jobs.claim_job(job.job_id)
    jobs.finish_job(job, "complete", "Done")
    replay = [item async for item in progress_generator(job.job_id, after=int(event["id"]))]
    assert [item["event"] for item in replay] == ["progress", "complete"]


def test_reservation_status_unknown_id_duplicate_and_expiry() -> None:
    with TestClient(app) as client:
        reserved = client.post("/api/analysis-jobs")
        assert reserved.status_code == 201
        job_id = reserved.json()["job_id"]
        assert client.get(f"/api/analysis-jobs/{job_id}").json()["status"] == "pending"
        assert client.get("/api/progress/unknown").status_code == 404
        assert (
            client.get(f"/api/progress/{job_id}", headers={"Last-Event-ID": "bad"}).status_code
            == 400
        )
        job = jobs.claim_job(job_id)
        duplicate = client.post(
            "/api/analyze",
            files={"audio": ("test.wav", b"invalid", "audio/wav")},
            data={"target_text": "hello", "job_id": job_id},
        )
        assert duplicate.status_code == 409
        jobs.finish_job(job, "cancelled", "Cancelled")
        with patch("app.services.jobs.time.monotonic", return_value=job.updated_at + 301):
            assert client.get(f"/api/analysis-jobs/{job_id}").status_code == 404


@pytest.mark.asyncio
async def test_slow_subscriber_and_history_are_bounded() -> None:
    job = jobs.create_job()
    stream = progress_generator(job.job_id)
    await anext(stream)
    for n in range(200):
        await send_progress_update(job.job_id, 0.5, str(n))
    assert len(job.history) == jobs.HISTORY_SIZE
    assert next(iter(job.subscribers)).qsize() == jobs.HISTORY_SIZE
    await stream.aclose()


def test_http_job_contract_replays_completed_submission() -> None:
    from unittest.mock import AsyncMock

    with TestClient(app) as client:
        job_id = client.post("/api/analysis-jobs").json()["job_id"]
        with (
            patch(
                "app.api.analyze.save_upload_to_temp",
                AsyncMock(return_value="/nonexistent/test.wav"),
            ),
            patch(
                "app.api.analyze._run_analysis_pipeline", AsyncMock(return_value={"success": True})
            ),
        ):
            response = client.post(
                "/api/analyze",
                files={"audio": ("test.wav", b"audio", "audio/wav")},
                data={"target_text": "hello", "job_id": job_id},
            )
        assert response.status_code == 200
        assert response.json()["job_id"] == job_id
        assert client.get(f"/api/analysis-jobs/{job_id}").json()["status"] == "complete"
        stream = client.get(f"/api/progress/{job_id}", headers={"Last-Event-ID": "1"})
        assert stream.status_code == 200
        assert "event: complete" in stream.text
        assert "event: progress" in stream.text


def test_pending_reservations_are_bounded_and_expire(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import HTTPException

    monkeypatch.setattr(jobs, "MAX_JOBS", 1)
    first = jobs.create_job()
    with pytest.raises(HTTPException) as full:
        jobs.create_job()
    assert full.value.status_code == 503
    with patch("app.services.jobs.time.monotonic", return_value=first.updated_at + 301):
        assert jobs.create_job().job_id != first.job_id
