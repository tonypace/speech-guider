# Analysis progress and inference ownership

## HTTP contract

1. `POST /api/analysis-jobs` reserves a job and returns HTTP 201 with `job_id`
   and `events_url`. Reserve immediately before uploading.
2. Open `GET /api/progress/{job_id}`. Each subscriber gets its own stream and
   recent history, including events emitted before it connected.
3. Submit multipart `POST /api/analyze` with `audio`, `target_text`, and `job_id`.
   The response remains synchronous and includes the same `job_id`. Existing
   callers can omit the reservation; the endpoint creates one automatically.
4. `GET /api/analysis-jobs/{job_id}` returns status and latest sequence.

Job states are `pending`, `running`, and one of `complete`, `failed`, `cancelled`.
A reservation can be submitted once; duplicates return HTTP 409. Unknown/expired
jobs return HTTP 404. Validation errors before claim leave a reservation pending.
Failed/busy submissions after claim terminate that reservation; retry with a new ID.

SSE event names are `progress`, `complete`, `failed`, `cancelled`, `heartbeat`,
and `expired`. Progress and terminal payloads contain job ID, progress fraction,
message, step, status, and sequence. Event IDs are sequence numbers. Reconnect with
`Last-Event-ID` or `?after=N`; clients should close after a terminal/expired event.
The browser recorder reserves and subscribes before upload, writes messages as text,
and closes its stream when the HTTP request finishes. SSE unavailability leaves
ordinary HTTP analysis usable.

## Bounds and ownership

The registry retains 64 recent events per job and 256 jobs per process. Pending
reservations and terminal jobs expire after five idle minutes, checked on registry
access. Running jobs do not expire while they own resources. Slow subscribers have
64 queued events; the oldest queued event is dropped on overflow. Sequence gaps
are therefore possible, and replay is bounded rather than a durable event log.
Disconnecting a subscriber never removes another subscriber or the job history.

Analysis results/audio are not stored in the progress registry. Upload/model/Praat
work remains owned by the HTTP workflow. All three heavy workflows (analysis,
reference generation, Prosody Lab) use one process-local inference gate. Competing
requests get HTTP 503. Blocking stages run in worker threads.

Cancellation cannot stop a Python worker thread. Cancellation is propagated only
after the owning task/worker finishes; only then is the inference gate released
and the uploaded file deleted. Cancelled upload conversion similarly drains its
worker and removes its resulting temporary file. There is no background job result
retrieval or explicit cancel endpoint in this contract. Browser disconnect alone
does not guarantee ASGI cancels the handler.

Use one Uvicorn worker process. Multiple processes would have separate gates and
job registries; supporting them requires shared admission, event, and storage
infrastructure. Job IDs are local capabilities, not authentication; do not expose
this local application as an authenticated multi-user service without that design.
