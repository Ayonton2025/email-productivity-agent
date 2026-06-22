"""
Workflow automation background tasks
"""

from app.tasks.celery_app import celery_app as celery
from datetime import datetime
from sqlalchemy import select, and_
from app.models.database import AsyncSessionLocal
from app.core.security import logger
from app.tasks.async_runner import run_async

@celery.task(bind=True, max_retries=2)
def execute_scheduled_workflows(self):
    """Sync wrapper to execute workflows that are due to run."""
    return run_async(_execute_scheduled_workflows(self))


async def _execute_scheduled_workflows(self):
    """Async implementation that runs scheduled workflows."""
    try:
        async with AsyncSessionLocal() as session:
            from app.models.workflow_models import Workflow, WorkflowExecution

            # Get active workflows
            result = await session.execute(
                select(Workflow).where(Workflow.is_active == True)
            )
            workflows = result.scalars().all()

            executed = 0

            for workflow in workflows:
                try:
                    # Check if workflow should execute
                    # This would depend on your workflow trigger logic

                    # Create execution record
                    execution = WorkflowExecution(
                        workflow_id=workflow.id,
                        user_id=workflow.user_id,
                        started_at=datetime.utcnow(),
                        status="running"
                    )
                    session.add(execution)

                    # Execute workflow steps
                    # ... workflow execution logic ...

                    execution.status = "completed"
                    execution.completed_at = datetime.utcnow()
                    executed += 1

                except Exception as e:
                    logger.error(f"Error executing workflow {workflow.id}: {str(e)}")
                    continue

            await session.commit()
            logger.info(f"Executed {executed} workflows")
            return {"executed": executed, "status": "success"}

    except Exception as exc:
        logger.error(f"execute_scheduled_workflows failed: {str(exc)}")
        try:
            self.retry(exc=exc, countdown=60)
        except Exception:
            raise


@celery.task(bind=True, max_retries=2)
def send_due_reminders(self):
    """Sync wrapper to send reminders for due tasks."""
    return run_async(_send_due_reminders(self))


async def _send_due_reminders(self):
    """Async implementation that sends due reminders."""
    try:
        async with AsyncSessionLocal() as session:
            from app.models.workflow_models import Reminder

            # Get reminders that are due
            now = datetime.utcnow()
            result = await session.execute(
                select(Reminder).where(
                    and_(
                        Reminder.due_at <= now,
                        Reminder.sent == False
                    )
                )
            )
            reminders = result.scalars().all()

            sent = 0
            for reminder in reminders:
                try:
                    # Send reminder notification
                    # This could be email, in-app notification, etc.

                    reminder.sent = True
                    reminder.sent_at = datetime.utcnow()
                    sent += 1

                except Exception as e:
                    logger.error(f"Error sending reminder {reminder.id}: {str(e)}")
                    continue

            await session.commit()
            logger.info(f"Sent {sent} reminders")
            return {"sent": sent, "status": "success"}

    except Exception as exc:
        logger.error(f"send_due_reminders failed: {str(exc)}")
        try:
            self.retry(exc=exc, countdown=30)
        except Exception:
            raise
