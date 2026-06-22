from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/fila/", consumers.FilaConsumer.as_asgi()),
    path("ws/control/", consumers.ControlConsumer.as_asgi()),
]