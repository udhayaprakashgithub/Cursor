from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse

from .models import AuditLog, Deployment, JobExecution, JobLog, ScheduledJob, VirtualEnv


@staff_member_required
def health(request):
    return JsonResponse(
        {
            'virtualenvs': VirtualEnv.objects.count(),
            'deployments': Deployment.objects.count(),
            'jobs': ScheduledJob.objects.count(),
            'executions': JobExecution.objects.count(),
            'logs': JobLog.objects.count(),
            'audits': AuditLog.objects.count(),
        }
    )
