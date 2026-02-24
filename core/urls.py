from django.urls import path

from .views import health

urlpatterns = [
    path('health/', health, name='health'),
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('run/<int:task_id>/', views.run_now, name='run_now'),
    path('toggle/<int:task_id>/', views.toggle_task, name='toggle_task'),
    path('delete/<int:task_id>/', views.delete_task, name='delete_task'),
]
