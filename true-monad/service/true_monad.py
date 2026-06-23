"""Filesystem service for the True Monad workbench.

The module deliberately uses only the Python standard library. Files remain the
source of truth; the web application is only a controlled view over them.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ROOT = Path(__file__).resolve().parents[1]
NEXT = ROOT / "next"
CURRENT = ROOT / "current"
END = ROOT / "end"
ARCHIVE = ROOT / "archive"

CURRENT_SCHEMAS = {
    "question": ["id", "round_id", "created_at", "question", "context", "status", "decision"],
    "advice": ["id", "round_id", "created_at", "advice", "rationale", "status", "decision"],
    "todo": ["id", "round_id", "created_at", "task", "priority", "status", "note"],
    "work": ["id", "round_id", "created_at", "action", "result", "status"],
}

ARCHIVE_FILES = {
    "question": "archive_questions.csv",
    "advice": "archive_advice.csv",
    "todo": "archive_todo.csv",
    "work": "archive_work.csv",
}

INSTRUCTION_PATTERN = re.compile(r"^(I|Q|A|T)-([A-Za-z0-9_-]+)\.md$")
TRIGGERS = {"1", "11", "111"}


class PactError(ValueError):
    """A user-facing file-contract violation."""


def utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.replace(temp_name, str(path))
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def _write_csv_header(path: Path, fields: List[str]) -> None:
    stream = io.StringIO(newline="")
    csv.writer(stream).writerow(fields)
    _atomic_write(path, stream.getvalue())


def ensure_workspace() -> None:
    for folder in (NEXT, CURRENT, END, ARCHIVE):
        folder.mkdir(parents=True, exist_ok=True)
    monad = CURRENT / "compressed_monad.md"
    if not monad.exists():
        _atomic_write(monad, "# Compressed Monad\n\n尚未建立项目认知环境。\n")
    understanding = CURRENT / "instruction_understanding.md"
    if not understanding.exists():
        _atomic_write(understanding, "")
    for kind, fields in CURRENT_SCHEMAS.items():
        path = CURRENT / ("current_%s.csv" % kind)
        if not path.exists():
            _write_csv_header(path, fields)


def _read_csv(path: Path, expected: Optional[List[str]] = None) -> Dict[str, Any]:
    if not path.exists():
        return {"rows": [], "error": None, "headers": expected or []}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []
            if expected is not None and headers != expected:
                raise PactError("%s 表头应为 %s，实际为 %s" % (path.name, expected, headers))
            rows = list(reader)
        return {"rows": rows, "error": None, "headers": headers}
    except (csv.Error, UnicodeError, PactError) as exc:
        return {"rows": [], "error": str(exc), "headers": []}


def validate_workspace() -> List[Dict[str, str]]:
    ensure_workspace()
    checks: List[Dict[str, str]] = []
    for kind, fields in CURRENT_SCHEMAS.items():
        result = _read_csv(CURRENT / ("current_%s.csv" % kind), fields)
        checks.append({
            "name": "current_%s.csv" % kind,
            "status": "error" if result["error"] else "ok",
            "message": result["error"] or "%d 条记录" % len(result["rows"]),
        })
    names = [p.name for p in NEXT.iterdir() if p.is_file() and not p.name.startswith(".")]
    invalid = [name for name in names if not INSTRUCTION_PATTERN.match(name)]
    checks.append({
        "name": "next/ 文件命名",
        "status": "error" if invalid else "ok",
        "message": "非法文件：%s" % ", ".join(invalid) if invalid else "%d 个待处理文件" % len(names),
    })
    return checks


def _markdown_files(folder: Path) -> List[Dict[str, Any]]:
    result = []
    for path in sorted(folder.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = path.stat()
        result.append({
            "name": path.name,
            "content": _read_text(path),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
            "size": stat.st_size,
        })
    return result


def _archive_preview(filename: str, limit: int = 300) -> Dict[str, Any]:
    result = _read_csv(ARCHIVE / filename)
    rows = result["rows"][-limit:]
    rows.reverse()
    return {"name": filename, "headers": result["headers"], "rows": rows, "error": result["error"]}


def snapshot() -> Dict[str, Any]:
    ensure_workspace()
    interactions = {}
    for kind, fields in CURRENT_SCHEMAS.items():
        interactions[kind] = _read_csv(CURRENT / ("current_%s.csv" % kind), fields)
    archives = [
        "archive_rounds.csv", "archive_instructions.csv", "archive_instruction_understanding.csv",
        "archive_questions.csv", "archive_advice.csv", "archive_todo.csv",
        "archive_work.csv", "archive_end.csv",
    ]
    checks = validate_workspace()
    return {
        "generated_at": utc_now(),
        "root": str(ROOT),
        "monad": _read_text(CURRENT / "compressed_monad.md"),
        "understanding": _read_text(CURRENT / "instruction_understanding.md"),
        "instructions": _markdown_files(NEXT),
        "outputs": _markdown_files(END),
        "interactions": interactions,
        "archives": [_archive_preview(name) for name in archives if (ARCHIVE / name).exists()],
        "checks": checks,
        "trigger": json.loads(_read_text(ROOT / "trigger.signal") or "null"),
    }


def _safe_instruction_name(filename: str) -> str:
    name = Path(filename).name
    if name != filename or not INSTRUCTION_PATTERN.match(name):
        raise PactError("指令文件名必须符合 I/Q/A/T-标识.md")
    return name


def save_instruction(filename: str, content: str) -> Dict[str, str]:
    ensure_workspace()
    name = _safe_instruction_name(filename)
    if not isinstance(content, str):
        raise PactError("指令内容必须是文本")
    _atomic_write(NEXT / name, content)
    return {"name": name, "saved_at": utc_now()}


def create_instruction(kind: str, content: str) -> Dict[str, str]:
    if kind not in {"I", "Q", "A", "T"}:
        raise PactError("未知指令类型")
    ensure_workspace()
    numbers = []
    for path in NEXT.glob(kind + "-*.md"):
        match = re.match(r"^%s-(\d+)\.md$" % kind, path.name)
        if match:
            numbers.append(int(match.group(1)))
    filename = "%s-%03d.md" % (kind, max(numbers or [0]) + 1)
    return save_instruction(filename, content)


def delete_instruction(filename: str) -> None:
    path = NEXT / _safe_instruction_name(filename)
    if not path.exists():
        raise PactError("指令文件不存在")
    path.unlink()


def respond_to_interaction(kind: str, item_id: str, content: str) -> Dict[str, str]:
    prefix = {"question": "Q", "advice": "A", "todo": "T"}.get(kind)
    if not prefix:
        raise PactError("该交互类型不支持回复")
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "-", str(item_id)).strip("-")
    if not safe_id:
        raise PactError("交互 ID 无效")
    return save_instruction("%s-%s.md" % (prefix, safe_id), content)


def emit_trigger(signal: str) -> Dict[str, str]:
    if signal not in TRIGGERS:
        raise PactError("触发器只能是 1、11 或 111")
    payload = {"signal": signal, "created_at": utc_now(), "status": "pending"}
    _atomic_write(ROOT / "trigger.signal", json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return payload


def _append_rows(path: Path, fields: List[str], rows: Iterable[Dict[str, Any]]) -> int:
    rows = list(rows)
    if not rows:
        return 0
    exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def archive_round() -> Dict[str, Any]:
    ensure_workspace()
    checks = validate_workspace()
    errors = [item for item in checks if item["status"] == "error"]
    if errors:
        raise PactError("归档中止：%s" % "; ".join(item["message"] for item in errors))
    archived_at = utc_now()
    round_id = datetime.now().astimezone().strftime("R-%Y%m%d-%H%M%S")
    counts: Dict[str, int] = {}

    instruction_rows = []
    for item in _markdown_files(NEXT):
        match = INSTRUCTION_PATTERN.match(item["name"])
        instruction_rows.append({
            "round_id": round_id, "archived_at": archived_at, "type": match.group(1),
            "filename": item["name"], "content": item["content"],
        })
    counts["instructions"] = _append_rows(
        ARCHIVE / "archive_instructions.csv",
        ["round_id", "archived_at", "type", "filename", "content"], instruction_rows,
    )

    understanding = _read_text(CURRENT / "instruction_understanding.md")
    counts["understanding"] = _append_rows(
        ARCHIVE / "archive_instruction_understanding.csv",
        ["round_id", "archived_at", "content"],
        [{"round_id": round_id, "archived_at": archived_at, "content": understanding}] if understanding.strip() else [],
    )

    output_rows = [{"round_id": round_id, "archived_at": archived_at, "filename": item["name"], "content": item["content"]} for item in _markdown_files(END)]
    counts["outputs"] = _append_rows(
        ARCHIVE / "archive_end.csv", ["round_id", "archived_at", "filename", "content"], output_rows,
    )

    for kind, fields in CURRENT_SCHEMAS.items():
        current = _read_csv(CURRENT / ("current_%s.csv" % kind), fields)
        rows = []
        for row in current["rows"]:
            archived = dict(row)
            archived["archived_at"] = archived_at
            archived["archive_round_id"] = round_id
            rows.append(archived)
        archive_fields = ["archive_round_id", "archived_at"] + fields
        counts[kind] = _append_rows(ARCHIVE / ARCHIVE_FILES[kind], archive_fields, rows)

    counts["round"] = _append_rows(
        ARCHIVE / "archive_rounds.csv",
        ["round_id", "archived_at", "compressed_monad", "instruction_count", "output_count"],
        [{"round_id": round_id, "archived_at": archived_at, "compressed_monad": _read_text(CURRENT / "compressed_monad.md"),
          "instruction_count": counts["instructions"], "output_count": counts["outputs"]}],
    )

    for path in list(NEXT.glob("*.md")) + list(END.glob("*.md")):
        path.unlink()
    _atomic_write(CURRENT / "instruction_understanding.md", "")
    for kind, fields in CURRENT_SCHEMAS.items():
        _write_csv_header(CURRENT / ("current_%s.csv" % kind), fields)
    return {"round_id": round_id, "archived_at": archived_at, "counts": counts}
