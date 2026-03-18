from django.contrib import admin
from .models import WebhookEntry

@admin.register(WebhookEntry)
class WebhookEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'endpoint', 'agent', 'user', 'processed', 'created_at')
    list_filter = ('endpoint', 'processed', 'created_at')
    search_fields = ('endpoint', 'agent__name', 'user__email')
    readonly_fields = ('headers', 'payload', 'raw_body', 'processing_result')
    raw_id_fields = ('agent', 'user')
    date_hierarchy = 'created_at'