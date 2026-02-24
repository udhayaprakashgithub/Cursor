# A037-SRS-001 Navitas Automation – AI Control Center

Django-based scheduler control center covering deployment management, virtualenv mapping, scheduling, execution, retries, monitoring, and audit.

## Delivered capabilities
- Virtual environment registry (`VirtualEnv`).
- Deployment + version management (`Deployment`, `DeploymentVersion`) with ZIP metadata and extraction path tracking.
- Advanced scheduler (`ScheduledJob`) with trigger types:
  - `folder`, `once`, `minutes`, `hourly`, `daily`, `weekly`, `monthly`, `yearly`, `cron`.
- Runtime execution tracking (`JobExecution`) and per-attempt logging (`JobLog`).
- Full audit model (`AuditLog`) for create/update/delete/run/enable/disable/cancel events.
- Django Admin operations:
  - Run now async
  - Enable/disable selected
  - Reset counters
  - CSV export on Audit/Execution/Log
- Django Q based queuing with safe sync fallback when queue engine is unavailable.

## Architecture
- `core/models.py` : all domain entities + validation + counters.
- `core/tasks.py` : queue and execute jobs (`main.py`) inside selected virtualenv.
- `core/scheduler_service.py` : schedule synchronization helpers + folder cycle hooks.
- `core/admin.py` : operational admin console and bulk actions.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
python manage.py qcluster
```

Open:
- Admin: `http://127.0.0.1:8000/admin/`
- Health endpoint: `http://127.0.0.1:8000/health/`

## Environment variables
- `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `DEPLOYMENT_FOLDER`

## Notes
- Folder watch worker loop is modeled by `run_folder_watch_cycle()` and should be invoked by a background worker/cron task.
- Execution timeout defaults to 7200 seconds if `timeout_override=0`.
