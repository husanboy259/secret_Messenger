from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from accounts.models import Account, Contact, Event, User, UserSettings


class AccountInline(admin.TabularInline):
    model = Account
    extra = 0
    fields = ['label', 'slot_order', 'status', 'last_used_at']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'username',
        'display_name',
        'email',
        'emoji_status',
        'is_online',
        'last_seen',
    ]
    list_filter = ['is_online', 'is_staff', 'is_superuser', 'is_active']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Messger', {'fields': ('display_name', 'bio', 'avatar', 'emoji_status')}),
    )
    inlines = [AccountInline]


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'label', 'user', 'slot_order', 'status', 'last_used_at']
    list_filter = ['status']
    search_fields = ['label', 'user__username']
    raw_id_fields = ['user']


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'theme', 'accent', 'send_on_enter', 'show_birthday_banner']
    list_filter = ['theme', 'send_on_enter', 'show_birthday_banner']
    raw_id_fields = ['user']


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['id', 'owner', 'user', 'nickname', 'is_favorite']
    list_filter = ['is_favorite']
    search_fields = ['nickname', 'user__username']
    raw_id_fields = ['owner', 'user']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['id', 'owner', 'person_name', 'date', 'kind', 'emoji']
    list_filter = ['kind']
    search_fields = ['person_name']
    raw_id_fields = ['owner']
