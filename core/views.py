from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ScheduledTaskForm
from .models import ScheduledTask
from .scheduler_service import run_task, sync_task


def dashboard(request):
    if request.method == 'POST':
        form = ScheduledTaskForm(request.POST, request.FILES)
        if form.is_valid():
            task = form.save()
            sync_task(task)
            messages.success(request, 'Task scheduled successfully.')
            return redirect('dashboard')
    else:
        form = ScheduledTaskForm()

    tasks = ScheduledTask.objects.order_by('-created_at')
    return render(request, 'core/dashboard.html', {'form': form, 'tasks': tasks})


@require_POST
def run_now(request, task_id):
    task = get_object_or_404(ScheduledTask, id=task_id)
    run_task(task.id)
    messages.success(request, f'Executed: {task.name}')
    return redirect('dashboard')


@require_POST
def toggle_task(request, task_id):
    task = get_object_or_404(ScheduledTask, id=task_id)
    task.enabled = not task.enabled
    task.save(update_fields=['enabled'])
    sync_task(task)
    messages.success(request, f'Updated status for {task.name}')
    return redirect('dashboard')


@require_POST
def delete_task(request, task_id):
    task = get_object_or_404(ScheduledTask, id=task_id)
    task.main_file.delete(save=False)
    task.delete()
    messages.success(request, 'Task deleted.')
    return redirect('dashboard')
