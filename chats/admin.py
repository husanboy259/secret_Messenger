from django.contrib import admin

from chats.models import (
    Attachment,
    Call,
    Chat,
    ChatMember,
    Folder,
    Message,
    ReadReceipt,
    Reaction,
)


class ChatMemberInline(admin.TabularInline):
    model = ChatMember
    extra = 0
    raw_id_fields = ['user']


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        '__str__',
        'type',
        'folder',
        'is_favorite',
        'is_muted',
        'created_by',
        'created_at',
    ]
    list_filter = ['type', 'is_channel', 'is_bot', 'is_favorite', 'is_muted', 'created_at']
    search_fields = ['name']
    raw_id_fields = ['created_by', 'pinned_message']
    list_select_related = ['folder', 'created_by']
    inlines = [ChatMemberInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'chat', 'sender', 'preview', 'is_read', 'created_at']
    list_filter = ['is_read', 'is_edited', 'is_deleted', 'created_at']
    search_fields = ['content']
    raw_id_fields = ['chat', 'sender', 'reply_to', 'attachment']
    list_select_related = ['chat', 'sender']
    date_hierarchy = 'created_at'

    @admin.display(description='Matn')
    def preview(self, obj):
        return obj.content[:50] if not obj.is_deleted else '(o\'chirilgan)'


@admin.register(ReadReceipt)
class ReadReceiptAdmin(admin.ModelAdmin):
    list_display = ['message', 'user', 'read_at']
    raw_id_fields = ['message', 'user']


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ['message', 'user', 'kind']
    list_filter = ['kind']
    raw_id_fields = ['message', 'user']


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'slug', 'owner', 'kind', 'position']
    list_filter = ['kind']
    search_fields = ['title', 'slug']
    raw_id_fields = ['owner']


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'file_name', 'kind', 'size', 'created_at']
    list_filter = ['kind', 'created_at']
    search_fields = ['file_name']
    date_hierarchy = 'created_at'


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ['id', 'chat', 'initiator', 'kind', 'status', 'duration', 'created_at']
    list_filter = ['kind', 'status', 'created_at']
    raw_id_fields = ['chat', 'initiator']
    date_hierarchy = 'created_at'
