from django.conf import settings
from django.db import models
from django.utils import timezone


class Folder(models.Model):
    """Sidebar bo'limlari: All Chats, PC Favorite, Bots, Football, Python / Linux / HTML."""

    class Kind(models.TextChoices):
        SYSTEM = 'system', 'Tizim'           # All Chats, Bots, Edit
        CUSTOM = 'custom', 'Foydalanuvchi'   # PC Favorite, Football, Python…

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='folders'
    )
    slug = models.SlugField(max_length=40)                 # all | favorite | bots | football
    title = models.CharField(max_length=60)                # "PC Favorite"
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.CUSTOM)
    icon = models.CharField(max_length=40, default='i-folder')
    position = models.PositiveIntegerField(default=0)
    accent = models.CharField(max_length=20, blank=True)   # "#8b5cf6"

    class Meta:
        ordering = ['position', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'slug'], name='unique_folder_slug_per_owner'
            ),
        ]

    def __str__(self):
        return f'{self.owner}: {self.title}'


class Attachment(models.Model):
    class Kind(models.TextChoices):
        IMAGE = 'image', 'Rasm'
        VIDEO = 'video', 'Video'
        AUDIO = 'audio', 'Audio'
        VOICE = 'voice', 'Ovozli xabar'
        FILE = 'file', 'Fayl'

    kind = models.CharField(max_length=6, choices=Kind.choices, default=Kind.FILE)
    file = models.FileField(upload_to='attachments/%Y/%m/')
    file_name = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    size = models.PositiveBigIntegerField(default=0)                  # bytes
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration = models.PositiveIntegerField(null=True, blank=True)     # sekund
    thumbnail = models.ImageField(upload_to='attachments/thumbs/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name or f'attachment:{self.pk}'


class Chat(models.Model):
    class Type(models.TextChoices):
        PRIVATE = 'private', 'Shaxsiy'
        GROUP = 'group', 'Guruh'

    type = models.CharField(
        max_length=10,
        choices=Type.choices,
        default=Type.PRIVATE,
    )
    name = models.CharField(max_length=120, blank=True)
    avatar = models.URLField(blank=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='chats',
        through='ChatMember',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_chats',
    )
    folder = models.ForeignKey(
        'Folder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chats',
    )
    is_channel = models.BooleanField(default=False)
    is_bot = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)
    is_muted = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    pinned_message = models.ForeignKey(
        'Message',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pinned_in_chats',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name or f'Chat #{self.pk}'

    def members_names(self):
        return ', '.join(self.members.values_list('username', flat=True))

    @property
    def last_message(self):
        return self.messages.order_by('-created_at').first()


class ChatMember(models.Model):
    """A'zo ro'yxati. Guruhda rol va oxirgi o'qilgan xabar saqlanadi."""

    class Role(models.TextChoices):
        MEMBER = 'member', "A'zo"
        ADMIN = 'admin', 'Admin'

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_message = models.ForeignKey(
        'Message',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='read_by_members',
    )

    class Meta:
        unique_together = ('chat', 'user')
        ordering = ['joined_at']

    def __str__(self):
        return f'{self.user} in {self.chat}'


class Message(models.Model):
    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    content = models.TextField(blank=True)
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
    )
    attachment = models.ForeignKey(
        'Attachment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages',
    )
    client_id = models.CharField(
        max_length=40,
        blank=True,
        default='',
        help_text='Frontend yuborgan vaqtincha id (dedup uchun).',
    )
    is_read = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at', 'id']
        indexes = [
            models.Index(fields=['chat', 'created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['sender', 'client_id'],
                condition=~models.Q(client_id=''),
                name='unique_sender_client_id',
            ),
        ]

    def __str__(self):
        if self.is_deleted:
            return f'{self.sender}: (o\'chirilgan)'
        return f'{self.sender}: {self.content[:30]}'


class ReadReceipt(models.Model):
    """Kim qaysi xabarni qachon o'qigan."""

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='read_receipts',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='read_receipts',
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user')
        ordering = ['read_at']

    def __str__(self):
        return f'{self.user} read {self.message_id}'


class Reaction(models.Model):
    class Kind(models.TextChoices):
        LIKE = 'like', 'Like'
        LOVE = 'love', 'Love'
        LAUGH = 'laugh', 'Haha'
        SAD = 'sad', 'Sad'

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='reactions',
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    kind = models.CharField(max_length=10, choices=Kind.choices)

    class Meta:
        unique_together = ('message', 'user')
        ordering = ['kind']

    def __str__(self):
        return f'{self.user} -> {self.kind}'


class Call(models.Model):
    class Kind(models.TextChoices):
        VOICE = 'voice', 'Ovozli'
        VIDEO = 'video', 'Video'

    class Status(models.TextChoices):
        MISSED = 'missed', 'Javobsiz'
        OUTGOING = 'outgoing', 'Chiquvchi'
        INCOMING = 'incoming', 'Kiruvchi'
        ENDED = 'ended', 'Tugadi'

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='calls')
    initiator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    kind = models.CharField(max_length=5, choices=Kind.choices, default=Kind.VOICE)
    status = models.CharField(
        max_length=8, choices=Status.choices, default=Status.MISSED
    )
    started_at = models.DateTimeField(null=True, blank=True)
    duration = models.PositiveIntegerField(default=0)   # sekund
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.chat} — {self.kind} ({self.status})'


ONLINE_WINDOW_SECONDS = 60


def unread_count_for(user):
    """Foydalanuvchi uchun o'qilmagan xabarlar soni."""
    return (
        Message.objects.filter(chat__members=user, is_read=False, is_deleted=False)
        .exclude(sender=user)
        .count()
    )


def is_online(user):
    """`last_seen` yaqinda bo'lsa foydalanuvchi onlineda hisoblanadi."""
    if not user.is_online or not user.last_seen:
        return False
    return (timezone.now() - user.last_seen).total_seconds() < ONLINE_WINDOW_SECONDS


__all__ = [
    'Attachment',
    'Call',
    'Chat',
    'ChatMember',
    'Folder',
    'Message',
    'ReadReceipt',
    'Reaction',
    'is_online',
    'unread_count_for',
]
