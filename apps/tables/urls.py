from django.urls import path

from apps.tables import views

urlpatterns = [
    path("health/", views.health, name="api-health"),
    path("games/", views.create_game, name="game-list"),
    path("games/<uuid:game_id>/", views.game_detail, name="game-detail"),
    path("games/<uuid:game_id>/actions/", views.game_action, name="game-action"),
    path("games/<uuid:game_id>/review/", views.game_review, name="game-review"),
    path("games/<uuid:game_id>/advice/", views.game_advice, name="game-advice"),
]
