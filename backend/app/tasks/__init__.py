# Make sure task modules are imported so tasks get registered with Celery
from . import email_tasks
from . import ai_tasks
from . import campaign_tasks
from . import workflow_tasks
from . import integration_tasks
from . import billing_tasks
from . import maintenance_tasks
from . import phase1_tasks
