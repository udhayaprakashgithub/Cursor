from django import forms
from django.utils import timezone

from .models import ScheduledTask


class ScheduledTaskForm(forms.ModelForm):
    class Meta:
        model = ScheduledTask
        fields = [
            'name',
            'main_file',
            'venv_path',
            'arguments',
            'schedule_type',
            'run_at',
            'interval_minutes',
            'cron_expression',
            'enabled',
        ]
        widgets = {
            'run_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean(self):
        cleaned = super().clean()
        schedule_type = cleaned.get('schedule_type')
        run_at = cleaned.get('run_at')
        interval = cleaned.get('interval_minutes')
        cron_expr = cleaned.get('cron_expression')

        if schedule_type == 'once' and not run_at:
            self.add_error('run_at', 'Run at is required for one-time tasks.')

        if schedule_type == 'once' and run_at and run_at < timezone.now():
            self.add_error('run_at', 'Run at must be in the future.')

        if schedule_type == 'interval' and (not interval or interval < 1):
            self.add_error('interval_minutes', 'Provide interval minutes (>= 1).')

        if schedule_type == 'cron' and not cron_expr:
            self.add_error('cron_expression', 'Cron expression is required for cron tasks.')

        return cleaned
