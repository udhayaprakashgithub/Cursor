import subprocess
import time
from pathlib import Path

from django.utils import timezone

from .models import JobExecution, JobLog


def _resolve_python(venv_path: str) -> Path:
    venv = Path(venv_path)
    unix = venv / 'bin' / 'python'
    windows = venv / 'Scripts' / 'python.exe'
    return unix if unix.exists() else windows


def execute_job(execution_id: int):
    execution = JobExecution.objects.select_related('job', 'job__deployment_version__virtualenv').get(id=execution_id)
    job = execution.job
    deployment_version = job.deployment_version
    execution.started_at = timezone.now()
    execution.cached_status = 'running'
    execution.save(update_fields=['started_at', 'cached_status'])

    attempts = max(1, job.retry_attempts + 1)
    for attempt in range(1, attempts + 1):
        log = JobLog.objects.create(
            execution=execution,
            job=job,
            job_name=job.name,
            deployment_version=deployment_version,
            started_at=timezone.now(),
            attempt_number=attempt,
            total_attempts=attempts,
        )
        try:
            python_exe = _resolve_python(deployment_version.virtualenv.path)
            script_path = Path(deployment_version.extracted_path) / 'main.py'
            if not python_exe.exists():
                raise RuntimeError(f'Python executable not found at {python_exe}')
            if not script_path.exists():
                raise RuntimeError(f'main.py not found at {script_path}')

            result = subprocess.run(
                [str(python_exe), str(script_path)],
                capture_output=True,
                text=True,
                check=False,
                timeout=job.timeout_override or 7200,
                cwd=script_path.parent,
            )
            log.finished_at = timezone.now()
            log.exit_code = result.returncode
            log.success = result.returncode == 0
            log.message = f'STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}'
            log.save()
            if log.success:
                execution.cached_status = 'success'
                break
        except Exception as exc:  # noqa: BLE001
            log.finished_at = timezone.now()
            log.success = False
            log.message = str(exc)
            log.save()
        if attempt < attempts and job.retry_delay:
            time.sleep(job.retry_delay)
            continue

    execution.finished_at = timezone.now()
    execution.update_cached_status()
    latest = execution.logs.order_by('-id').first()
    job.record_execution_result(bool(latest and latest.success))


def queue_job_execution(job, triggered_by=None, trigger_source='scheduled', trigger_params=None):
    trigger_params = trigger_params or {}
    execution = JobExecution.objects.create(
        job=job,
        job_name=job.name,
        trigger_type=job.trigger_type,
        trigger_source=trigger_source,
        trigger_params=trigger_params,
        triggered_by=triggered_by,
        django_q_task_id='pending',
    )

    try:
        from django_q.tasks import async_task

        task_id = async_task('core.tasks.execute_job', execution.id)
        execution.django_q_task_id = str(task_id)
        execution.save(update_fields=['django_q_task_id'])
    except Exception:
        execute_job(execution.id)
        execution.django_q_task_id = 'sync-fallback'
        execution.save(update_fields=['django_q_task_id'])

    return execution
