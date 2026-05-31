from django.contrib import admin

from apps.tables.models import GameSession


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "difficulty", "status", "created_at", "updated_at")
    list_filter = ("difficulty", "status")
    search_fields = ("id",)

