# Make sure task modules are imported so tasks get registered with Celery
from . import ai_tasks as ai_tasks
from . import billing_tasks as billing_tasks
from . import campaign_tasks as campaign_tasks
from . import email_tasks as email_tasks
from . import integration_tasks as integration_tasks
from . import maintenance_tasks as maintenance_tasks
from . import phase1_tasks as phase1_tasks
from . import workflow_tasks as workflow_tasks
