from __future__ import annotations

import os
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hackforge.utils import utc_now_iso, write_json


@dataclass
class RunJournal:
    """Durable, privacy-safe lifecycle state for long-running analyses."""

    run_dir: Path | None = None
    state: dict[str, Any] = field(default_factory=dict)

    def attach(self, run_dir: Path, *, provider: str, search_profile: str) -> None:
        self.run_dir = run_dir
        now = utc_now_iso()
        self.state = {
            "status": "running",
            "stage": "initialization",
            "created_at": now,
            "updated_at": now,
            "pid": os.getpid(),
            "provider": provider,
            "search_profile": search_profile,
            "log_file": str((run_dir / "run.log").resolve()),
        }
        self._persist()
        self._log("INFO", "run initialized", provider=provider, search_profile=search_profile)

    def checkpoint(self, stage: str, **counts: int) -> None:
        if self.run_dir is None:
            return
        self.state.update({"status": "running", "stage": stage, "updated_at": utc_now_iso()})
        if counts:
            self.state.setdefault("counts", {}).update(counts)
        self._persist()
        self._log("INFO", "stage started", stage=stage, **counts)

    def complete(self, *, output_ids: list[str]) -> None:
        if self.run_dir is None:
            return
        self.state.update(
            {
                "status": "complete",
                "stage": "complete",
                "updated_at": utc_now_iso(),
                "output_ids": output_ids,
            }
        )
        self._persist()
        self._log("INFO", "run completed", output_ids=output_ids)

    def fail(self, error: BaseException) -> None:
        if self.run_dir is None:
            return
        self.state.update(
            {
                "status": "cancelled" if isinstance(error, KeyboardInterrupt) else "failed",
                "stage": self.state.get("stage", "unknown"),
                "updated_at": utc_now_iso(),
                "error_type": type(error).__name__,
                "error": str(error)[:1000],
            }
        )
        self._persist()
        self._log(
            "ERROR",
            "run failed",
            stage=self.state.get("stage", "unknown"),
            error_type=type(error).__name__,
            error=str(error),
        )
        if self.run_dir is not None:
            log_path = self.run_dir / "run.log"
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write("".join(traceback.format_exception(type(error), error, error.__traceback__)))
                handle.write("\n")
            os.chmod(log_path, 0o600)

    def _log(self, level: str, message: str, **fields: Any) -> None:
        if self.run_dir is None:
            return
        suffix = " ".join(f"{key}={value!r}" for key, value in fields.items())
        line = f"{utc_now_iso()} {level} {message}"
        if suffix:
            line += f" {suffix}"
        log_path = self.run_dir / "run.log"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        os.chmod(log_path, 0o600)

    def _persist(self) -> None:
        if self.run_dir is not None:
            write_json(self.run_dir / "run-status.json", self.state)
