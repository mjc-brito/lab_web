from django.contrib import admin
from .models import LabSettings


@admin.register(LabSettings)
class LabSettingsAdmin(admin.ModelAdmin):
    list_display = ["session_duration_minutes", "entry_timeout_minutes"]

    def has_add_permission(self, request):
        return not LabSettings.objects.exists()