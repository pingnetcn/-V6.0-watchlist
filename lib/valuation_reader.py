"""
Parse val_<code>_<tag>.txt reports into structured data.

How to extend:
    New report format? Add a new parser function, dispatch in parse_metadata()
    New section? Update parse_full_report() section regex
    v6.97+ JSON block is canonical; pre-v6.97 flat key:value is fallback

Public API:
    list_versions(code) -> list[Path]
    latest_version(code) -> Path | None
    parse_metadata(path) -> dict
    parse_full_report(path) -> {metadata: dict, sections: dict[int, str]}
    read_credibility_emoji(metadata) -> str
"""
import json
import re
from pathlib import Path
from typing import Optional

SCHEMA_VERSION = 2  # bumped for pre-v6.97 fallback

VAL_DIR = Path("E:/stock/Val")


def list_versions(code: str) -> list[Path]:
    if not VAL_DIR.exists():
        return []
    return sorted(VAL_DIR.glob(f"val_{code}_*.txt"))


def latest_version(code: str) -> Optional[Path]:
    """Return the most recently modified report for this code.

    Uses file mtime, NOT version tag — tags like v_power / v18 are batch IDs
    not chronological, so the heuristic must be mtime-based.
    """
    versions = list_versions(code)
    if not versions:
        return None
    return max(versions, key=lambda p: p.stat().st_mtime)


def _parse_v97_metadata(text: str) -> dict:
    match = re.search(r"## 元数据\s*```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    raise ValueError("No v6.97+ JSON metadata block found")


def _parse_pre_v97_metadata(text: str) -> dict:
    """Parse flat `key: value` lines from pre-v6.97 files."""
    result = {}
    # Try to extract code from title line like "华润三九(000999)"
    code_match = re.search(r"\((\d{6})\)", text)
    if code_match:
        result["code"] = code_match.group(1)

    for line in text.splitlines():
        line = line.strip()
        if not line or ":" not in line or line.startswith("#"):
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key.startswith("valuation_") or key in ("code", "name", "version", "rating"):
            # Keep both clean and original versions for compatibility
            clean_key = key.replace("valuation_", "")
            result[clean_key] = value
            result[key] = value  # Also keep original key
    return result


def parse_metadata(path: Path) -> dict:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    try:
        return _parse_v97_metadata(text)
    except (ValueError, json.JSONDecodeError):
        return _parse_pre_v97_metadata(text)


def parse_full_report(path: Path) -> dict:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    metadata = parse_metadata(path)
    sections = {}
    # Split by `## N.` markers
    parts = re.split(r"^##\s*(\d+(?:\.\d+)?)\.\s*(.+)$", text, flags=re.MULTILINE)
    # parts = [preamble, num1, title1, body1, num2, title2, body2, ...]
    for i in range(1, len(parts), 3):
        if i + 2 < len(parts):
            num = int(float(parts[i]))
            body = parts[i + 2].strip()
            sections[num] = body
    return {"metadata": metadata, "sections": sections}


def read_credibility_emoji(metadata: dict) -> str:
    return metadata.get("credibility_emoji") or {
        "高": "🟢", "中": "🟡", "低": "🟠", "不可信": "🔴"
    }.get(metadata.get("credibility"), "❓")
