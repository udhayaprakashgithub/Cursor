from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ScheduledTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('main_file', models.FileField(upload_to='scripts/')),
                ('venv_path', models.CharField(help_text='Folder path that contains your virtual environment.', max_length=500)),
                ('arguments', models.CharField(blank=True, help_text='Optional arguments passed to main.py', max_length=300)),
                ('schedule_type', models.CharField(choices=[('once', 'Run once'), ('interval', 'Interval (minutes)'), ('cron', 'Cron expression')], default='once', max_length=20)),
                ('run_at', models.DateTimeField(blank=True, null=True)),
                ('interval_minutes', models.PositiveIntegerField(blank=True, null=True)),
                ('cron_expression', models.CharField(blank=True, help_text='Use crontab format: m h dom mon dow', max_length=100)),
                ('enabled', models.BooleanField(default=True)),
                ('last_run', models.DateTimeField(blank=True, null=True)),
                ('last_output', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
