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
import shlex
import subprocess
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone

scheduler = BackgroundScheduler(timezone='UTC')


def _python_from_venv(venv_path: str) -> Path:
    base = Path(venv_path).expanduser()
    unix_python = base / 'bin' / 'python'
    windows_python = base / 'Scripts' / 'python.exe'
    if unix_python.exists():
        return unix_python
    return windows_python


def run_task(task_id: int):
    from .models import ScheduledTask

    task = ScheduledTask.objects.get(id=task_id)
    if not task.enabled:
        return

    python_exe = _python_from_venv(task.venv_path)
    script_path = Path(task.main_file.path)

    if not python_exe.exists():
        task.last_run = timezone.now()
        task.last_output = f'Virtual environment python not found at {python_exe}'
        task.save(update_fields=['last_run', 'last_output'])
        return

    cmd = [str(python_exe), str(script_path)] + shlex.split(task.arguments or '')

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=script_path.parent,
        timeout=600,
        check=False,
    )

    combined_output = f'STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}\nExit code: {result.returncode}'
    task.last_run = timezone.now()
    task.last_output = combined_output
    task.save(update_fields=['last_run', 'last_output'])


def sync_task(task):
    job_id = f'task-{task.id}'
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    if not task.enabled:
        return

    if task.schedule_type == 'once' and task.run_at:
        scheduler.add_job(run_task, DateTrigger(run_date=task.run_at), args=[task.id], id=job_id, replace_existing=True)
    elif task.schedule_type == 'interval' and task.interval_minutes:
        scheduler.add_job(
            run_task,
            IntervalTrigger(minutes=task.interval_minutes),
            args=[task.id],
            id=job_id,
            replace_existing=True,
        )
    elif task.schedule_type == 'cron' and task.cron_expression:
        scheduler.add_job(
            run_task,
            CronTrigger.from_crontab(task.cron_expression),
            args=[task.id],
            id=job_id,
            replace_existing=True,
        )


def resync_all_tasks():
    from .models import ScheduledTask

    for task in ScheduledTask.objects.all():
        sync_task(task)


def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        try:
            resync_all_tasks()
        except Exception:
            pass
