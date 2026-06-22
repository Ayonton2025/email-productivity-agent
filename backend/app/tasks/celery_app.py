"""
Celery configuration for background task processing

Tasks include:
- Email intelligence processing
- Campaign management
- Workflow automation
- Integration syncs
- Billing operations
"""

from celery import Celery  # type: ignore
from celery.schedules import crontab  # type: ignore
from app.core.config import settings
import logging

# Initialize Celery app
celery_app = Celery(
    "email_productivity_agent",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'app.tasks.email_tasks',
        'app.tasks.ai_tasks',
        'app.tasks.campaign_tasks',
        'app.tasks.workflow_tasks',
        'app.tasks.integration_tasks',
        'app.tasks.billing_tasks',
        'app.tasks.maintenance_tasks',
        'app.tasks.phase1_tasks',
        'app.tasks.meeting_tasks',
    ]
)

# Configure Celery
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minute hard limit
    task_soft_time_limit=25 * 60,  # 25 minute soft limit
    
    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
)

# Scheduled tasks
celery_app.conf.beat_schedule = {
    # Email processing
    "process-new-emails": {
        "task": "app.tasks.email_tasks.process_new_emails",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
        "options": {"queue": "email"}
    },
    
    "sync-email-accounts": {
        "task": "app.tasks.email_tasks.sync_email_accounts",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
        "options": {"queue": "email"}
    },
    
    # AI Processing
    "process-email-intelligence": {
        "task": "app.tasks.ai_tasks.process_email_intelligence",
        "schedule": crontab(minute="*/10"),  # Every 10 minutes
        "options": {"queue": "ai"}
    },
    
    # Campaign management
    "send-campaign-emails": {
        "task": "app.tasks.campaign_tasks.send_campaign_emails",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
        "options": {"queue": "campaigns"}
    },
    
    "process-campaign-replies": {
        "task": "app.tasks.campaign_tasks.process_campaign_replies",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
        "options": {"queue": "campaigns"}
    },
    
    "execute-warmup-schedule": {
        "task": "app.tasks.campaign_tasks.execute_warmup_schedule",
        "schedule": crontab(minute=0, hour="*/2"),  # Every 2 hours
        "options": {"queue": "campaigns"}
    },
    
    # Automation
    "execute-scheduled-workflows": {
        "task": "app.tasks.workflow_tasks.execute_scheduled_workflows",
        "schedule": crontab(minute="*/10"),  # Every 10 minutes
        "options": {"queue": "workflows"}
    },
    
    "send-due-reminders": {
        "task": "app.tasks.workflow_tasks.send_due_reminders",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
        "options": {"queue": "workflows"}
    },
    
    # Integration syncs
    "sync-crm-contacts": {
        "task": "app.tasks.integration_tasks.sync_crm_contacts",
        "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
        "options": {"queue": "integrations"}
    },
    
    # Billing
    "reset-monthly-credits": {
        "task": "app.tasks.billing_tasks.reset_monthly_credits",
        "schedule": crontab(minute=0, hour=0, day_of_month=1),  # Every month on day 1
        "options": {"queue": "billing"}
    },

    "reset-daily-free-credits": {
        "task": "app.tasks.billing_tasks.reset_daily_free_credits",
        "schedule": crontab(minute=0, hour=0),  # Daily at midnight UTC
        "options": {"queue": "billing"}
    },
    
    "check-subscription-renewals": {
        "task": "app.tasks.billing_tasks.check_subscription_renewals",
        "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
        "options": {"queue": "billing"}
    },
    
    # Cleanup
    "cleanup-old-data": {
        "task": "app.tasks.maintenance_tasks.cleanup_old_data",
        "schedule": crontab(minute=0, hour=2),  # 2 AM daily
        "options": {"queue": "maintenance"}
    },
    
    "archive-completed-campaigns": {
        "task": "app.tasks.maintenance_tasks.archive_completed_campaigns",
        "schedule": crontab(minute=0, hour=3),  # 3 AM daily
        "options": {"queue": "maintenance"}
    },

    # Phase 1
    "generate-daily-briefings-for-due-users": {
        "task": "app.tasks.phase1_tasks.generate_daily_briefings_for_due_users",
        "schedule": crontab(minute=0),  # hourly, timezone-aware dispatch per user
        "options": {"queue": "ai"}
    },

    "process-auto-followups": {
        "task": "app.tasks.phase1_tasks.process_auto_followups",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
        "options": {"queue": "email"}
    },

    "meeting-followup-task": {
        "task": "app.tasks.meeting_tasks.meeting_followup_task",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "workflows"},
    },
}

# Ensure Celery discovers task modules in the app.tasks package
celery_app.autodiscover_tasks(['app.tasks'])

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    celery_app.start()
