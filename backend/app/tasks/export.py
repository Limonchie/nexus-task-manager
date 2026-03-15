"""Export tasks (CSV) as Celery background jobs."""

from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.export.export_tasks_csv")
def export_tasks_csv(user_id: int) -> dict[str, str]:
    """Export user tasks to CSV. In production, use sync SQLAlchemy or store result in Redis/S3."""
    # Placeholder: real implementation would query DB (sync engine in worker) and return file path or content
    return {"filename": "tasks.csv", "status": "completed", "message": "Export job finished"}
