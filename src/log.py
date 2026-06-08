from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RunLog:
    def __init__(self, path: Path = Path("data/runs.jsonl")) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, kind: str, params: dict[str, Any], result: dict[str, Any]) -> str:
        now = datetime.now(timezone.utc)
        run_id = f"{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        record = {
            "id": run_id,
            "ts": now.isoformat().replace("+00:00", "Z"),
            "kind": kind,
            "params": params,
            "result": result,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return run_id

    def tail(self, n: int = 10) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()[-n:]
        return [json.loads(line) for line in lines if line.strip()]
