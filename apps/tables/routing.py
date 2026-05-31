from django.urls import path

from apps.tables.consumers import TableConsumer

websocket_urlpatterns = [
    path("ws/tables/<uuid:game_id>/", TableConsumer.as_asgi()),
]

