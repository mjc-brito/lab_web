from django.urls import path
from . import views

urlpatterns = [
    path("queue_control/", views.queue_control_view, name="queue_control"),
]