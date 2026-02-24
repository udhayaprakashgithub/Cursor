from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F
from django.utils import timezone


class TriggerType(models.TextChoices):
    FOLDER = 'folder', 'Folder Watch'
    ONCE = 'once', 'Once'
    MINUTES = 'minutes', 'Minutes'
    HOURLY = 'hourly', 'Hourly'
    DAILY = 'daily', 'Daily'
    WEEKLY = 'weekly', 'Weekly'
    MONTHLY = 'monthly', 'Monthly'
    YEARLY = 'yearly', 'Yearly'
    CRON = 'cron', 'Cron'


class VirtualEnv(models.Model):
    name = models.CharField(max_length=120, unique=True)
    path = models.CharField(max_length=500, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_virtualenvs',
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.path})'


class Deployment(models.Model):
    custom_name = models.CharField(max_length=160)
    unique_id = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_deployments',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.custom_name} [{self.unique_id}]'


class DeploymentVersion(models.Model):
    deployment = models.ForeignKey(Deployment, on_delete=models.CASCADE, related_name='versions')
    virtualenv = models.ForeignKey(VirtualEnv, on_delete=models.PROTECT, related_name='deployment_versions')
    version_number = models.PositiveIntegerField(default=1)
    zip_file = models.FileField(upload_to='deployment_zips/')
    extracted_path = models.CharField(max_length=600, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_deployment_versions',
    )

    class Meta:
        unique_together = ('deployment', 'version_number')
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.pk is None and not self.version_number:
            latest = DeploymentVersion.objects.filter(deployment=self.deployment).aggregate(models.Max('version_number'))
            self.version_number = (latest['version_number__max'] or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.deployment.custom_name} v{self.version_number}'


class ScheduledJob(models.Model):
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)
    trigger_type = models.CharField(max_length=20, choices=TriggerType.choices, default=TriggerType.ONCE)
    watch_path = models.CharField(max_length=600, blank=True)
    file_pattern = models.CharField(max_length=120, blank=True, default='*')
    cron = models.CharField(max_length=120, blank=True)
    minutes_interval = models.PositiveIntegerField(null=True, blank=True)
    run_at = models.DateTimeField(null=True, blank=True)
    deployment_version = models.ForeignKey(
        DeploymentVersion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='scheduled_jobs',
    )
    app_name = models.CharField(max_length=80, blank=True)
    allowed_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='allowed_jobs')
    retry_attempts = models.PositiveIntegerField(default=0)
    retry_delay = models.PositiveIntegerField(default=60)
    timeout_override = models.PositiveIntegerField(default=0)
    tags = models.CharField(max_length=200, blank=True)
    q_schedule_id = models.CharField(max_length=120, blank=True)
    total_executions = models.PositiveIntegerField(default=0)
    success_executions = models.PositiveIntegerField(default=0)
    failed_executions = models.PositiveIntegerField(default=0)
    last_result = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['enabled', 'trigger_type']),
            models.Index(fields=['app_name']),
        ]

    def clean(self):
        if self.trigger_type == TriggerType.ONCE and not self.run_at:
            raise ValidationError({'run_at': 'Run at is required for once trigger.'})
        if self.trigger_type == TriggerType.MINUTES and not self.minutes_interval:
            raise ValidationError({'minutes_interval': 'Minutes interval required.'})
        if self.trigger_type == TriggerType.CRON and not self.cron:
            raise ValidationError({'cron': 'Cron expression required.'})
        if self.trigger_type == TriggerType.FOLDER and not self.watch_path:
            raise ValidationError({'watch_path': 'Watch path required for folder trigger.'})

    def record_execution_result(self, success: bool):
        updates = {'total_executions': F('total_executions') + 1}
        if success:
            updates['success_executions'] = F('success_executions') + 1
            updates['last_result'] = 'success'
        else:
            updates['failed_executions'] = F('failed_executions') + 1
            updates['last_result'] = 'failed'
        ScheduledJob.objects.filter(pk=self.pk).update(**updates)

    def __str__(self):
        return self.name


class JobExecution(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('unknown', 'Unknown'),
    ]

    job = models.ForeignKey(ScheduledJob, on_delete=models.CASCADE, related_name='executions')
    job_name = models.CharField(max_length=180)
    trigger_type = models.CharField(max_length=20, choices=TriggerType.choices)
    trigger_source = models.CharField(max_length=30, default='scheduled')
    trigger_params = models.JSONField(default=dict, blank=True)
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    django_q_task_id = models.CharField(max_length=120, blank=True)
    queued_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    cached_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    cached_duration = models.FloatField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-queued_at']
        indexes = [models.Index(fields=['cached_status', 'queued_at'])]

    def update_cached_status(self):
        latest_log = self.logs.order_by('-id').first()
        if latest_log:
            if latest_log.finished_at and latest_log.success is True:
                self.cached_status = 'success'
            elif latest_log.finished_at and latest_log.success is False:
                self.cached_status = 'failed'
            elif latest_log.started_at and not latest_log.finished_at:
                self.cached_status = 'running'
            if latest_log.execution_duration:
                self.cached_duration = latest_log.execution_duration
        elif (timezone.now() - self.queued_at).total_seconds() < 900:
            self.cached_status = 'queued'
        else:
            self.cached_status = 'unknown'
        self.save(update_fields=['cached_status', 'cached_duration'])

    def __str__(self):
        return f'Execution {self.id} - {self.job_name}'


class JobLog(models.Model):
    execution = models.ForeignKey(JobExecution, on_delete=models.CASCADE, related_name='logs')
    job = models.ForeignKey(ScheduledJob, on_delete=models.CASCADE, related_name='logs')
    job_name = models.CharField(max_length=180)
    deployment_version = models.ForeignKey(DeploymentVersion, on_delete=models.SET_NULL, null=True, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    success = models.BooleanField(null=True, blank=True)
    message = models.TextField(blank=True)
    attempt_number = models.PositiveIntegerField(default=1)
    total_attempts = models.PositiveIntegerField(default=1)
    execution_duration = models.FloatField(default=0)
    exit_code = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [models.Index(fields=['success', 'started_at'])]

    def save(self, *args, **kwargs):
        if self.finished_at and self.started_at and not self.execution_duration:
            self.execution_duration = (self.finished_at - self.started_at).total_seconds()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Log {self.id} {self.job_name}'


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('run', 'Run'),
        ('enable', 'Enable'),
        ('disable', 'Disable'),
        ('cancel', 'Cancel'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    object_repr = models.CharField(max_length=255)
    changes = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [models.Index(fields=['action', 'timestamp'])]

    def __str__(self):
        return f'{self.action} - {self.object_repr}'
