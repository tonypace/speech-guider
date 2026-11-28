"""Restore and verify local mHuBERT-147 + ctc_v1 + CMUdict IPA assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

from huggingface_hub import snapshot_download

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "external" / "mhubert-147"
ENCODER_REPO_ID = "utter-project/mHuBERT-147"
CTC_HEAD_REPO_ID = "istomin9192/mHuBERT-147-ipa-head"
CMUDICT_URL = "https://raw.githubusercontent.com/cmusphinx/cmudict/master/cmudict.dict"

# ARPAbet -> istomin9192/mHuBERT-147-ipa-head ctc_v1 45-phone IPA vocabulary.
# Stress digits (0/1/2) are stripped before lookup, except AH0 (schwa) vs AH1/AH2
# which both collapse to ə in the 45-phone ctc_v1 inventory (ʌ is absent).
ARPABET_TO_CTC_IPA: dict[str, str] = {
    "AA": "ɑ",
    "AE": "æ",
    "AH": "ə",
    "AO": "ɔ",
    "AW": "aʊ",
    "AY": "aɪ",
    "B": "b",
    "CH": "tʃ",
    "D": "d",
    "DH": "ð",
    "EH": "ɛ",
    "ER": "ɹ̩",
    "EY": "eɪ",
    "F": "f",
    "G": "g",
    "HH": "h",
    "IH": "ɪ",
    "IY": "i",
    "JH": "dʒ",
    "K": "k",
    "L": "l",
    "M": "m",
    "N": "n",
    "NG": "ŋ",
    "OW": "oʊ",
    "OY": "ɔɪ",
    "P": "p",
    "R": "r",
    "S": "s",
    "SH": "ʃ",
    "T": "t",
    "TH": "θ",
    "UH": "ʊ",
    "UW": "u",
    "V": "v",
    "W": "w",
    "Y": "j",
    "Z": "z",
    "ZH": "ʒ",
}

_VARIANT_SUFFIX_RE = re.compile(r"\(\d+\)$")


def _sha256(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def _download_cmudict(dest_json: Path, valid_ipa: set[str]) -> int:
    req = urllib.request.Request(
        CMUDICT_URL,
        headers={"User-Agent": "speech-guider-asset-restore/1.0"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw_text = resp.read().decode("utf-8", errors="replace")

    lexicon: dict[str, list[list[str]]] = {}
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith(";;;"):
            continue
        # Strip inline comments if present
        comment_idx = line.find(" #")
        if comment_idx != -1:
            line = line[:comment_idx].strip()
        parts = line.split()
        if len(parts) < 2:
            continue
        raw_word = _VARIANT_SUFFIX_RE.sub("", parts[0]).lower()
        phones: list[str] = []
        valid = True
        for arpa in parts[1:]:
            base = re.sub(r"[012]$", "", arpa)
            ipa = ARPABET_TO_CTC_IPA.get(base)
            if ipa is None or (valid_ipa and ipa not in valid_ipa):
                valid = False
                break
            phones.append(ipa)
        if not valid or not phones:
            continue
        variants = lexicon.setdefault(raw_word, [])
        if phones not in variants:
            variants.append(phones)

    dest_json.write_text(
        json.dumps(lexicon, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return len(lexicon)


def _write_sha256sums(bundle_dir: Path) -> Path:
    manifest_path = bundle_dir / "SHA256SUMS"
    entries: list[str] = []
    for path in sorted(bundle_dir.rglob("*")):
        if not path.is_file() or path == manifest_path:
            continue
        rel = path.relative_to(bundle_dir).as_posix()
        entries.append(f"{_sha256(path)}  {rel}")
    manifest_path.write_text("\n".join(entries) + "\n", encoding="utf-8")
    return manifest_path


def verify_bundle(bundle_dir: Path) -> None:
    manifest_path = bundle_dir / "SHA256SUMS"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing SHA256SUMS in {bundle_dir}")
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(maxsplit=1)
        rel = rel.removeprefix("*").removeprefix("./")
        target = bundle_dir / rel
        if not target.is_file():
            raise FileNotFoundError(f"Missing staged asset: {target}")
        actual = _sha256(target)
        if actual != digest:
            raise ValueError(f"Checksum mismatch for {rel}: expected {digest}, got {actual}")


def restore(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    encoder_dir = output_dir / "encoder"
    snapshot_download(
        repo_id=ENCODER_REPO_ID,
        local_dir=str(encoder_dir),
        allow_patterns=[
            "config.json",
            "preprocessor_config.json",
            "model.safetensors",
            "README.md",
            "LICENSE*",
        ],
    )
    snapshot_download(
        repo_id=CTC_HEAD_REPO_ID,
        local_dir=str(output_dir),
        allow_patterns=["ctc_v1/*", "ipa_map.json", "README.md", "LICENSE*"],
    )
    ipa_map_path = output_dir / "ipa_map.json"
    valid_ipa: set[str] = set()
    if ipa_map_path.is_file():
        ipa_data = json.loads(ipa_map_path.read_text(encoding="utf-8"))
        if isinstance(ipa_data, dict):
            if isinstance(ipa_data.get("phone2id"), dict):
                valid_ipa = {
                    str(k) for k in ipa_data["phone2id"] if str(k) not in {"<blank>", "sil"}
                }
            else:
                for k, v in ipa_data.items():
                    if (
                        isinstance(k, str)
                        and not k.startswith("_")
                        and not k.isdigit()
                        and k != "<blank>"
                    ):
                        valid_ipa.add(k)
                    elif isinstance(v, str) and v != "<blank>":
                        valid_ipa.add(v)
    count = _download_cmudict(output_dir / "cmudict_ipa.json", valid_ipa)
    manifest = _write_sha256sums(output_dir)
    verify_bundle(output_dir)
    print(f"Staged mHuBERT-147 + ctc_v1 + {count} CMUdict entries in {output_dir}")
    print(f"Verified checksums in {manifest}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    out = args.output_dir.expanduser().resolve()
    if args.verify_only:
        verify_bundle(out)
        print(f"Verified mHuBERT bundle: {out}")
    else:
        restore(out)


if __name__ == "__main__":
    main()
