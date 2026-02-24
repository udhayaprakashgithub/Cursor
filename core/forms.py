from django import forms
from django.core.exceptions import ValidationError

from .models import ScheduledJob, TriggerType


class ScheduledJobAdminForm(forms.ModelForm):
    class Meta:
        model = ScheduledJob
        fields = '__all__'

    def clean(self):
        cleaned = super().clean()
        trigger = cleaned.get('trigger_type')
        if trigger == TriggerType.ONCE and not cleaned.get('run_at'):
            raise ValidationError('run_at is required for once trigger.')
        if trigger == TriggerType.MINUTES and not cleaned.get('minutes_interval'):
            raise ValidationError('minutes_interval is required for minutes trigger.')
        if trigger == TriggerType.CRON and not cleaned.get('cron'):
            raise ValidationError('cron is required for cron trigger.')
        if trigger == TriggerType.FOLDER and not cleaned.get('watch_path'):
            raise ValidationError('watch_path is required for folder trigger.')
        return cleaned
