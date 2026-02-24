import csv
from django.contrib import admin, messages
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.utils import timezone

from .forms import ScheduledJobAdminForm
from .models import (
    AuditLog,
    Deployment,
    DeploymentVersion,
    JobExecution,
    JobLog,
    ScheduledJob,
    VirtualEnv,
)
from .tasks import queue_job_execution


class CsvExportMixin:
    csv_fields = ()

    def export_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=export.csv'
        writer = csv.writer(response)
        writer.writerow(self.csv_fields)
        for obj in queryset[:10000]:
            writer.writerow([getattr(obj, f, '') for f in self.csv_fields])
        return response

    export_csv.short_description = 'Export selected to CSV'


@admin.register(VirtualEnv)
class VirtualEnvAdmin(admin.ModelAdmin):
    list_display = ('name', 'path', 'created_at', 'created_by')
    search_fields = ('name', 'path')


class DeploymentVersionInline(admin.TabularInline):
    model = DeploymentVersion
    extra = 0


@admin.register(Deployment)
class DeploymentAdmin(admin.ModelAdmin):
    list_display = ('custom_name', 'unique_id', 'created_at', 'created_by')
    search_fields = ('custom_name', 'unique_id')
    inlines = [DeploymentVersionInline]


@admin.register(DeploymentVersion)
class DeploymentVersionAdmin(admin.ModelAdmin):
    list_display = ('deployment', 'version_number', 'virtualenv', 'extracted_path', 'created_at')
    list_filter = ('deployment',)
    search_fields = ('deployment__custom_name', 'extracted_path')


class JobLogInline(admin.TabularInline):
    model = JobLog
    extra = 0
    fields = ('started_at', 'finished_at', 'success', 'attempt_number', 'execution_duration', 'exit_code')
    readonly_fields = fields
    can_delete = False


@admin.register(ScheduledJob)
class ScheduledJobAdmin(admin.ModelAdmin):
    form = ScheduledJobAdminForm
    list_display = (
        'id',
        'name',
        'app_name',
        'trigger_type',
        'enabled',
        'live_status',
        'next_run_display',
        'last_result',
        'stats_summary',
        'retry_display',
    )
    list_filter = ('enabled', 'trigger_type', 'app_name')
    search_fields = ('name', 'app_name', 'tags', 'deployment_version__deployment__custom_name')
    filter_horizontal = ('allowed_users',)
    actions = ('run_now_async', 'enable_selected', 'disable_selected', 'reset_execution_counters')
    inlines = [JobLogInline]

    def live_status(self, obj):
        last_exec = obj.executions.order_by('-queued_at').first()
        return last_exec.cached_status if last_exec else 'idle'

    def next_run_display(self, obj):
        if obj.trigger_type == 'folder':
            return 'watching'
        if obj.trigger_type == 'once':
            return obj.run_at or 'pending'
        if obj.q_schedule_id:
            return f'Schedule:{obj.q_schedule_id}'
        return 'No schedule'

    def stats_summary(self, obj):
        total = obj.total_executions or 0
        success = obj.success_executions or 0
        pct = round((success / total) * 100, 1) if total else 0
        return f'{success}/{total} ({pct}%)'

    def retry_display(self, obj):
        return f'{obj.retry_attempts} attempts, {obj.retry_delay}s delay'

    @admin.action(description='Run now async')
    def run_now_async(self, request, queryset):
        count = 0
        for job in queryset:
            if not job.deployment_version:
                continue
            queue_job_execution(job=job, triggered_by=request.user, trigger_source='manual', trigger_params={})
            AuditLog.objects.create(
                user=request.user,
                action='run',
                content_type=ContentType.objects.get_for_model(ScheduledJob),
                object_id=str(job.id),
                object_repr=job.name,
                changes={'trigger': 'manual'},
            )
            count += 1
        self.message_user(request, f'Queued {count} job(s).', level=messages.SUCCESS)

    @admin.action(description='Enable selected')
    def enable_selected(self, request, queryset):
        updated = queryset.update(enabled=True)
        self.message_user(request, f'Enabled {updated} jobs.', level=messages.SUCCESS)

    @admin.action(description='Disable selected')
    def disable_selected(self, request, queryset):
        updated = queryset.update(enabled=False)
        self.message_user(request, f'Disabled {updated} jobs.', level=messages.SUCCESS)

    @admin.action(description='Reset execution counters')
    def reset_execution_counters(self, request, queryset):
        queryset.update(total_executions=0, success_executions=0, failed_executions=0)
        self.message_user(request, 'Counters reset.', level=messages.SUCCESS)


@admin.register(JobExecution)
class JobExecutionAdmin(CsvExportMixin, admin.ModelAdmin):
    csv_fields = (
        'id',
        'job_id',
        'trigger_source',
        'trigger_type',
        'django_q_task_id',
        'queued_at',
        'started_at',
        'finished_at',
        'cached_duration',
        'cached_status',
    )
    list_display = (
        'id',
        'job',
        'trigger_source',
        'trigger_type',
        'triggered_by',
        'queued_at',
        'started_at',
        'finished_at',
        'cached_duration',
        'cached_status',
    )
    list_filter = ('cached_status', 'trigger_source', 'trigger_type')
    date_hierarchy = 'queued_at'
    search_fields = ('job_name', 'django_q_task_id')
    actions = ('export_csv',)


@admin.register(JobLog)
class JobLogAdmin(CsvExportMixin, admin.ModelAdmin):
    csv_fields = (
        'id',
        'job_id',
        'execution_id',
        'attempt_number',
        'started_at',
        'finished_at',
        'execution_duration',
        'exit_code',
        'success',
    )
    list_display = (
        'id',
        'job',
        'execution',
        'attempt_number',
        'started_at',
        'finished_at',
        'execution_duration',
        'exit_code',
        'success',
    )
    list_filter = ('success', 'started_at')
    search_fields = ('job_name', 'message')
    actions = ('export_csv',)


@admin.register(AuditLog)
class AuditLogAdmin(CsvExportMixin, admin.ModelAdmin):
    csv_fields = ('timestamp', 'user_id', 'action', 'object_repr', 'ip_address', 'changes')
    list_display = ('timestamp', 'user', 'action', 'object_repr', 'ip_address')
    list_filter = ('action',)
    search_fields = ('object_repr', 'user__username')
    readonly_fields = ('timestamp', 'user', 'action', 'ip_address', 'content_type', 'object_id', 'object_repr', 'changes')
    actions = ('export_csv',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
