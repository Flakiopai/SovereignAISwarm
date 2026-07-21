"""Minimal in-memory pipeline for passing tasks between agents."""

from __future__ import annotations

import itertools
import time
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    pending = "pending"
    taken = "taken"
    completed = "completed"
    failed = "failed"


class Task(BaseModel):
    id: str
    payload: Any = None
    from_agent: Optional[str] = None
    to_agent: Optional[str] = None
    status: TaskStatus = TaskStatus.pending
    result: Any = None
    error: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class Pipeline:
    """
    Simple task queue for agent-to-agent (or n8n node-to-node) handoff.

    In-memory only — enough to embed in workflows without extra infra.
    """

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._order: List[str] = []
        self._ids = itertools.count(1)

    def submit(
        self,
        payload: Any,
        *,
        from_agent: Optional[str] = None,
        to_agent: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Task:
        tid = task_id or f"task-{next(self._ids)}"
        if tid in self._tasks:
            raise ValueError(f"Task id already exists: {tid}")
        task = Task(
            id=tid,
            payload=payload,
            from_agent=from_agent,
            to_agent=to_agent,
            status=TaskStatus.pending,
        )
        self._tasks[tid] = task
        self._order.append(tid)
        return task

    def get(self, task_id: str) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError as e:
            raise KeyError(f"Unknown task id: {task_id}") from e

    def take(self, agent: Optional[str] = None) -> Optional[Task]:
        """Claim the next pending task, optionally filtered by to_agent."""
        for tid in self._order:
            task = self._tasks[tid]
            if task.status != TaskStatus.pending:
                continue
            if agent is not None and task.to_agent not in (None, agent):
                continue
            task.status = TaskStatus.taken
            task.updated_at = time.time()
            return task
        return None

    def complete(self, task_id: str, result: Any = None) -> Task:
        task = self.get(task_id)
        task.status = TaskStatus.completed
        task.result = result
        task.error = None
        task.updated_at = time.time()
        return task

    def fail(self, task_id: str, error: str) -> Task:
        task = self.get(task_id)
        task.status = TaskStatus.failed
        task.error = error
        task.updated_at = time.time()
        return task

    def pending(self, agent: Optional[str] = None) -> List[Task]:
        tasks = [
            t
            for t in self
            if t.status == TaskStatus.pending
            and (agent is None or t.to_agent in (None, agent))
        ]
        return tasks

    def to_dict(self) -> List[dict]:
        return [t.model_dump() for t in self]

    def __iter__(self) -> Iterator[Task]:
        for tid in self._order:
            yield self._tasks[tid]

    def __len__(self) -> int:
        return len(self._order)
