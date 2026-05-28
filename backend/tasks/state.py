from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any, Dict, Optional
from uuid import uuid4


def _utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


@dataclass
class TaskRecord:
    task_id: str
    status: str
    result: Any = None
    error: Optional[str] = None
    task_name: Optional[str] = None
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "task_name": self.task_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


_LOCK = Lock()
_TASKS: Dict[str, TaskRecord] = {}


def new_task_id() -> str:
    return uuid4().hex


def record_task_state(task_id: str, status: str, *, result: Any = None, error: Optional[str] = None, task_name: Optional[str] = None) -> Dict[str, Any]:
    record = TaskRecord(task_id=task_id, status=status, result=result, error=error, task_name=task_name)
    with _LOCK:
        _TASKS[task_id] = record
    return record.to_dict()


def get_task_state(task_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        record = _TASKS.get(task_id)
    return record.to_dict() if record else None
