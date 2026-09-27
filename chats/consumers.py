from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from chats.models import Chat, ChatMember, Message, ReadReceipt
from chats.serializers import MessageSerializer


class TokenAuthMixin:
    """`?token=<access>` orqali autentifikatsiya (WebSocket header'da token yo'q)."""

    async def resolve_user(self):
        from django.contrib.auth import get_user_model
        from rest_framework_simplejwt.tokens import AccessToken

        raw_query = (self.scope.get('query_string') or b'').decode()
        token = parse_qs(raw_query).get('token', [None])[0]
        if not token:
            return None
        try:
            user_id = AccessToken(token)['user_id']
        except Exception:
            return None
        return await self.get_user(user_id)

    @database_sync_to_async
    def get_user(self, user_id):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.filter(pk=user_id, is_active=True).first()


class BaseConsumer(TokenAuthMixin, AsyncJsonWebsocketConsumer):
    async def reject(self, code, reason):
        await self.accept()            # close olish uchun handshake bajarilishi kerak
        await self.send_json({'type': 'error', 'code': code, 'detail': reason})
        await self.close(code=code)


class ChatConsumer(BaseConsumer):
    async def connect(self):
        self.user = await self.resolve_user()
        if not self.user:
            await self.reject(4401, "Token yaroqsiz yoki yo'q.")
            return

        self.chat_id = int(self.scope['url_route']['kwargs']['chat_id'])
        if not await self.is_member(self.chat_id, self.user.pk):
            await self.reject(4403, "Bu chatga kirish huquqi yo'q.")
            return

        self.group_name = f'chat_{self.chat_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connected', 'chat_id': self.chat_id})
        await self.mark_presence(True)

    async def disconnect(self, code):
        if getattr(self, 'group_name', None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if getattr(self, 'user', None):
            await self.mark_presence(False)

    async def receive_json(self, content, **kwargs):
        action = content.get('action')

        if action == 'message.create':
            message = await self.create_message(content)
            if message is None:
                return await self.send_json(
                    {'type': 'error', 'code': 'invalid', 'detail': "Xabar bo'sh."}
                )
            await self.channel_layer.group_send(
                self.group_name, {'type': 'chat.message', 'payload': message}
            )
            await self.notify_message(self.chat_id, message)

        elif action == 'typing':
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat.typing',
                    'payload': {
                        'user_id': self.user.pk,
                        'username': self.user.username,
                        'is_typing': bool(content.get('is_typing')),
                    },
                },
            )

        elif action == 'read':
            await self.mark_read(content.get('message_id'))
            await self.channel_layer.group_send(
                self.group_name, {'type': 'chat.read', 'payload': {'user_id': self.user.pk}}
            )

        elif action == 'call.signal':
            # WebRTC signal relay — offer/answer/ice/end hammasi shu orqali
            # guruhga tarqatiladi, qabul qiluvchi `to` bo'yicha filtrlaydi.
            payload = dict(content.get('payload') or {})
            payload['from'] = self.user.pk
            await self.channel_layer.group_send(
                self.group_name,
                {'type': 'chat.call_signal', 'payload': payload},
            )

    # --- group event handlers ---
    async def chat_message(self, event):
        await self.send_json({'type': 'message.new', 'data': event['payload']})

    async def chat_typing(self, event):
        await self.send_json({'type': 'typing', 'data': event['payload']})

    async def chat_read(self, event):
        await self.send_json({'type': 'read', 'data': event['payload']})

    async def chat_updated(self, event):
        await self.send_json({'type': 'chat.updated', 'data': event['payload']})

    async def chat_call_signal(self, event):
        await self.send_json({'type': 'call.signal', 'data': event['payload']})

    # --- db helpers (sync -> async) ---
    @database_sync_to_async
    def is_member(self, chat_id, user_id):
        return ChatMember.objects.filter(chat_id=chat_id, user_id=user_id).exists()

    @database_sync_to_async
    def create_message(self, content):
        text = (content.get('text') or '').strip()
        client_id = content.get('client_id') or ''
        if not text and not content.get('attachment_id'):
            return None

        # client_id bo'yicha dedup — frontend reconnect qilsa xabar ikki marta kirmasin.
        if client_id:
            existing = Message.objects.filter(
                sender=self.user, client_id=client_id
            ).first()
            if existing:
                return MessageSerializer(existing).data

        chat = Chat.objects.filter(pk=self.chat_id).first()
        if not chat:
            return None

        msg = Message.objects.create(
            chat=chat,
            sender=self.user,
            content=text,
            reply_to_id=content.get('reply_to'),
            attachment_id=content.get('attachment_id'),
            client_id=client_id,
        )
        return MessageSerializer(msg).data

    @database_sync_to_async
    def member_ids(self, chat_id):
        """Chat a'zolari (yuboruvchidan tashqari) — global notification uchun."""
        return list(
            ChatMember.objects.filter(chat_id=chat_id)
            .exclude(user_id=self.user.pk)
            .values_list('user_id', flat=True)
        )

    async def notify_message(self, chat_id, message):
        """Yangi xabar haqida chat a'zolarini global kanal orqali xabardor qiladi."""
        for uid in await self.member_ids(chat_id):
            await self.channel_layer.group_send(
                f'user_{uid}',
                {
                    'type': 'notification',
                    'payload': {'event': 'message.new', 'chat_id': chat_id, 'message': message},
                },
            )

    @database_sync_to_async
    def mark_read(self, message_id):
        if not message_id:
            return None
        message = Message.objects.filter(
            pk=message_id, chat_id=self.chat_id
        ).first()
        if not message:
            return None
        ReadReceipt.objects.get_or_create(message=message, user=self.user)
        Message.objects.filter(chat_id=self.chat_id, is_read=False).update(
            is_read=True
        )
        return message.id

    @database_sync_to_async
    def mark_presence(self, online):
        from django.utils import timezone

        self.user.is_online = online
        self.user.last_seen = timezone.now()
        self.user.save(update_fields=['is_online', 'last_seen'])


class GlobalConsumer(BaseConsumer):
    """Bitta foydalanuvchining barcha chatlari uchun umumiy kanal."""

    async def connect(self):
        self.user = await self.resolve_user()
        if not self.user:
            await self.reject(4401, "Token yaroqsiz yoki yo'q.")
            return

        self.group_name = f'user_{self.user.pk}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connected', 'user_id': self.user.pk})

    async def disconnect(self, code):
        if getattr(self, 'group_name', None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        return

    async def notification(self, event):
        await self.send_json({'type': 'notification', 'data': event['payload']})
