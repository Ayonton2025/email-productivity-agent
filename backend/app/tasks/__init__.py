# Make sure task modules are imported so tasks get registered with Celery
from . import (
    ai_tasks,
    billing_tasks,
    campaign_tasks,
    email_tasks,
    integration_tasks,
    maintenance_tasks,
    phase1_tasks,
    workflow_tasks,
)
