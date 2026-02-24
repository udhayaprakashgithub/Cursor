from django.db import models


class ScheduledTask(models.Model):
    SCHEDULE_CHOICES = [
        ('once', 'Run once'),
        ('interval', 'Interval (minutes)'),
        ('cron', 'Cron expression'),
    ]

    name = models.CharField(max_length=120)
    main_file = models.FileField(upload_to='scripts/')
    venv_path = models.CharField(max_length=500, help_text='Folder path that contains your virtual environment.')
    arguments = models.CharField(max_length=300, blank=True, help_text='Optional arguments passed to main.py')

    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_CHOICES, default='once')
    run_at = models.DateTimeField(null=True, blank=True)
    interval_minutes = models.PositiveIntegerField(null=True, blank=True)
    cron_expression = models.CharField(max_length=100, blank=True, help_text='Use crontab format: m h dom mon dow')

    enabled = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    last_output = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
