from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.CharField(max_length=255, blank=True)
    avatar = models.URLField(blank=True)
    emoji_status = models.CharField(max_length=8, default='🕷️')
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.display_name or self.username


class Account(models.Model):
    """Brauzerdagi bitta login sloti (bir xil User bo'lishi mumkin)."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Faol'
        HIDDEN = 'hidden', 'Yashirilgan'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='accounts',
    )
    label = models.CharField(max_length=60, blank=True)   # "Work Account"
    slot_order = models.PositiveIntegerField(default=0)   # sidebar tartibi
    status = models.CharField(
        max_length=8, choices=Status.choices, default=Status.ACTIVE
    )
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['slot_order', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'label'], name='unique_account_label_per_user'
            ),
        ]

    def __str__(self):
        return self.label or self.user.username


class UserSettings(models.Model):
    """Frontend saqlaydigan sozlamalar (Night Mode, accent, Enter bilan yuborish)."""

    class Theme(models.TextChoices):
        NIGHT = 'night', 'Night'
        DAY = 'day', 'Day'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='settings'
    )
    theme = models.CharField(max_length=5, choices=Theme.choices, default=Theme.NIGHT)
    accent = models.CharField(max_length=20, default='#8b5cf6')
    send_on_enter = models.BooleanField(default=True)
    show_birthday_banner = models.BooleanField(default=True)
    wallpaper = models.URLField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'settings:{self.user_id}'


class Contact(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contacts'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contact_of'
    )
    nickname = models.CharField(max_length=100, blank=True)
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nickname', 'user__username']
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'user'], name='unique_contact_per_user'
            ),
        ]

    def __str__(self):
        return self.nickname or self.user.username


class Event(models.Model):
    """Tug'ilgan kun banner'i."""

    class Kind(models.TextChoices):
        BIRTHDAY = 'birthday', "Tug'ilgan kun"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='events'
    )
    person_name = models.CharField(max_length=100)
    date = models.DateField()
    kind = models.CharField(max_length=9, choices=Kind.choices, default=Kind.BIRTHDAY)
    emoji = models.CharField(max_length=8, default='🎂')

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f'{self.person_name} — {self.date}'
