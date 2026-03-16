from django.contrib import admin
from .models import Call

@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ('call_id', 'agent', 'duration_seconds', 'status', 'started_at')
    list_filter = ('status', 'started_at')
    search_fields = ('call_id', 'agent__name', 'agent__user__email')
    readonly_fields = ('call_data',)  # JSONField solo lectura