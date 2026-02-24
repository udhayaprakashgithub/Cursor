from django.utils import timezone

from .models import ScheduledJob, TriggerType
from .tasks import queue_job_execution


def sync_job_schedule(job: ScheduledJob):
    try:
        from django_q.models import Schedule
    except Exception:
        return None

    if job.q_schedule_id:
        Schedule.objects.filter(id=job.q_schedule_id).delete()
        job.q_schedule_id = ''

    if not job.enabled:
        job.save(update_fields=['q_schedule_id'])
        return None

    kwargs = {
        'func': 'core.tasks.queue_job_execution',
        'args': f'{job.id}',
    }

    if job.trigger_type == TriggerType.ONCE and job.run_at:
        schedule = Schedule.objects.create(schedule_type=Schedule.ONCE, next_run=job.run_at, **kwargs)
    elif job.trigger_type == TriggerType.MINUTES and job.minutes_interval:
        schedule = Schedule.objects.create(schedule_type=Schedule.MINUTES, minutes=job.minutes_interval, **kwargs)
    elif job.trigger_type == TriggerType.HOURLY:
        schedule = Schedule.objects.create(schedule_type=Schedule.HOURLY, **kwargs)
    elif job.trigger_type == TriggerType.DAILY:
        schedule = Schedule.objects.create(schedule_type=Schedule.DAILY, **kwargs)
    elif job.trigger_type == TriggerType.WEEKLY:
        schedule = Schedule.objects.create(schedule_type=Schedule.WEEKLY, **kwargs)
    elif job.trigger_type == TriggerType.MONTHLY:
        schedule = Schedule.objects.create(schedule_type=Schedule.MONTHLY, **kwargs)
    elif job.trigger_type == TriggerType.YEARLY:
        schedule = Schedule.objects.create(schedule_type=Schedule.YEARLY, **kwargs)
    elif job.trigger_type == TriggerType.CRON and job.cron:
        schedule = Schedule.objects.create(schedule_type=Schedule.CRON, cron=job.cron, **kwargs)
    else:
        schedule = None

    if schedule:
        job.q_schedule_id = str(schedule.id)
        job.save(update_fields=['q_schedule_id'])
    return schedule


def run_folder_watch_cycle():
    for job in ScheduledJob.objects.filter(enabled=True, trigger_type=TriggerType.FOLDER):
        queue_job_execution(job=job, trigger_source='folder_watch', trigger_params={'watch_path': job.watch_path})


def enqueue_due_once_jobs():
    now = timezone.now()
    for job in ScheduledJob.objects.filter(enabled=True, trigger_type=TriggerType.ONCE, run_at__lte=now):
        queue_job_execution(job=job)
        job.enabled = False
        job.save(update_fields=['enabled'])
