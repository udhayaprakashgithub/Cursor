from django.contrib import admin
from .models import ScheduledTask


@admin.register(ScheduledTask)
class ScheduledTaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'schedule_type', 'enabled', 'last_run', 'created_at')
    list_filter = ('schedule_type', 'enabled')
    search_fields = ('name', 'venv_path', 'cron_expression')
