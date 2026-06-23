"""Validate and archive one True Monad round from the command line."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "service"))

from true_monad import PactError, archive_round, validate_workspace  # noqa: E402


def main():
    if "--check" in sys.argv:
        checks = validate_workspace()
        print(json.dumps(checks, ensure_ascii=False, indent=2))
        raise SystemExit(1 if any(item["status"] == "error" for item in checks) else 0)
    if "--confirm" not in sys.argv:
        print("此操作会归档并清理本轮文件。请使用 --confirm 明确执行。")
        raise SystemExit(2)
    try:
        print(json.dumps(archive_round(), ensure_ascii=False, indent=2))
    except PactError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
