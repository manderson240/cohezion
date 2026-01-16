"""
Swarm Router - Lightweight Cloud Run service for task routing.

Acts as the "mailbox" for the swarm when the local machine is offline.
Queues incoming tasks from webhooks, email, or Slack into Firestore
for later processing by the local swarm.

Designed for deployment on Google Cloud Run with:
- High availability
- Auto-scaling
- Minimal cost when idle
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a task in the queue."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPriority(Enum):
    """Priority levels for tasks."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Task:
    """A task in the mission queue."""
    id: str
    payload: dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    result: dict[str, Any] | None = None
    error: str | None = None
    source: str = "api"  # api, webhook, slack, email
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "payload": self.payload,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "result": self.result,
            "error": self.error,
            "source": self.source,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return cls(
            id=data["id"],
            payload=data["payload"],
            status=TaskStatus(data.get("status", "pending")),
            priority=TaskPriority(data.get("priority", 2)),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data.get("updated_at", data["created_at"])),
            result=data.get("result"),
            error=data.get("error"),
            source=data.get("source", "api"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )


class SwarmRouter:
    """
    Cloud Run service for routing tasks to the local swarm.
    
    Features:
    - Receives tasks from multiple sources (webhooks, API, Slack)
    - Queues tasks in Firestore for local processing
    - Provides status endpoints for monitoring
    - Handles task retries and failure notifications
    """
    
    def __init__(
        self,
        project_id: str | None = None,
        collection_name: str = "mission_queue",
    ):
        """
        Initialize the Swarm Router.
        
        Args:
            project_id: GCP project ID (auto-detected on Cloud Run)
            collection_name: Firestore collection for the queue
        """
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self.collection_name = collection_name
        self._db: Any = None
        self._tasks: dict[str, Task] = {}  # In-memory fallback
    
    async def initialize(self) -> bool:
        """
        Initialize Firestore connection.
        
        Returns True if connected, False if using in-memory fallback.
        """
        try:
            from google.cloud import firestore
            self._db = firestore.AsyncClient(project=self.project_id)
            logger.info(f"Connected to Firestore: {self.project_id}")
            return True
        except ImportError:
            logger.warning(
                "google-cloud-firestore not installed. "
                "Using in-memory queue. "
                "Install with: pip install google-cloud-firestore"
            )
            return False
        except Exception as e:
            logger.error(f"Firestore connection failed: {e}")
            return False
    
    async def receive_task(
        self,
        payload: dict[str, Any],
        source: str = "api",
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> Task:
        """
        Receive and queue a new task.
        
        Args:
            payload: Task payload from client
            source: Source of the task
            priority: Task priority
            
        Returns:
            The created Task
        """
        task = Task(
            id=str(uuid4()),
            payload=payload,
            source=source,
            priority=priority,
        )
        
        if self._db:
            doc_ref = self._db.collection(self.collection_name).document(task.id)
            await doc_ref.set(task.to_dict())
        else:
            self._tasks[task.id] = task
        
        logger.info(f"Queued task {task.id} from {source}")
        return task
    
    async def get_pending_tasks(
        self,
        limit: int = 10,
    ) -> list[Task]:
        """
        Get pending tasks ordered by priority and creation time.
        
        Args:
            limit: Maximum number of tasks to return
            
        Returns:
            List of pending tasks
        """
        if self._db:
            query = (
                self._db.collection(self.collection_name)
                .where("status", "==", TaskStatus.PENDING.value)
                .order_by("priority", direction="DESCENDING")
                .order_by("created_at")
                .limit(limit)
            )
            docs = await query.get()
            return [Task.from_dict(doc.to_dict()) for doc in docs]
        else:
            pending = [
                t for t in self._tasks.values()
                if t.status == TaskStatus.PENDING
            ]
            pending.sort(key=lambda t: (-t.priority.value, t.created_at))
            return pending[:limit]
    
    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> Task | None:
        """
        Update a task's status.
        
        Args:
            task_id: Task ID
            status: New status
            result: Optional result data
            error: Optional error message
            
        Returns:
            Updated task, or None if not found
        """
        if self._db:
            doc_ref = self._db.collection(self.collection_name).document(task_id)
            doc = await doc_ref.get()
            
            if not doc.exists:
                return None
            
            update_data = {
                "status": status.value,
                "updated_at": datetime.now().isoformat(),
            }
            if result is not None:
                update_data["result"] = result
            if error is not None:
                update_data["error"] = error
            
            await doc_ref.update(update_data)
            
            task_data = doc.to_dict()
            task_data.update(update_data)
            return Task.from_dict(task_data)
        else:
            task = self._tasks.get(task_id)
            if task:
                task.status = status
                task.updated_at = datetime.now()
                if result:
                    task.result = result
                if error:
                    task.error = error
            return task
    
    async def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        if self._db:
            doc = await self._db.collection(self.collection_name).document(task_id).get()
            if doc.exists:
                return Task.from_dict(doc.to_dict())
            return None
        else:
            return self._tasks.get(task_id)
    
    async def get_queue_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        if self._db:
            collection = self._db.collection(self.collection_name)
            
            pending = len((await collection.where("status", "==", "pending").get()))
            processing = len((await collection.where("status", "==", "processing").get()))
            completed = len((await collection.where("status", "==", "completed").get()))
            failed = len((await collection.where("status", "==", "failed").get()))
            
            return {
                "pending": pending,
                "processing": processing,
                "completed": completed,
                "failed": failed,
                "total": pending + processing + completed + failed,
            }
        else:
            from collections import Counter
            status_counts = Counter(t.status.value for t in self._tasks.values())
            return {
                "pending": status_counts.get("pending", 0),
                "processing": status_counts.get("processing", 0),
                "completed": status_counts.get("completed", 0),
                "failed": status_counts.get("failed", 0),
                "total": len(self._tasks),
            }


# FastAPI application for Cloud Run deployment
def create_app() -> Any:
    """Create FastAPI app for Cloud Run deployment."""
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
    except ImportError:
        logger.error("FastAPI not installed")
        return None
    
    app = FastAPI(
        title="Cohezion Swarm Router",
        description="Cloud Run service for task routing",
        version="0.1.0",
    )
    
    router = SwarmRouter()
    
    class TaskPayload(BaseModel):
        data: dict[str, Any]
        source: str = "api"
        priority: int = 2
    
    @app.on_event("startup")
    async def startup():
        await router.initialize()
    
    @app.post("/tasks")
    async def create_task(payload: TaskPayload) -> dict[str, Any]:
        """Create a new task."""
        task = await router.receive_task(
            payload=payload.data,
            source=payload.source,
            priority=TaskPriority(payload.priority),
        )
        return task.to_dict()
    
    @app.get("/tasks/{task_id}")
    async def get_task(task_id: str) -> dict[str, Any]:
        """Get a task by ID."""
        task = await router.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task.to_dict()
    
    @app.get("/tasks")
    async def list_tasks(limit: int = 10) -> list[dict[str, Any]]:
        """List pending tasks."""
        tasks = await router.get_pending_tasks(limit)
        return [t.to_dict() for t in tasks]
    
    @app.get("/stats")
    async def get_stats() -> dict[str, Any]:
        """Get queue statistics."""
        return await router.get_queue_stats()
    
    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check."""
        return {"status": "healthy"}
    
    return app


if __name__ == "__main__":
    import uvicorn
    
    app = create_app()
    if app:
        port = int(os.environ.get("PORT", 8080))
        uvicorn.run(app, host="0.0.0.0", port=port)
