from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chats.models import Attachment, Call, Chat, ChatMember, Folder, Message, ReadReceipt, Reaction
from chats.permissions import IsChatMember, IsMessageOwnerOrAdmin
from chats.serializers import (
    AttachmentSerializer,
    CallSerializer,
    ChatMemberSerializer,
    ChatSerializer,
    FolderSerializer,
    MessageSerializer,
    ReactionSerializer,
)

# Sidebar'da har doim ko'rinadigan tizim papkalari (backend.md 4.3)
SYSTEM_FOLDERS = [
    {'slug': 'all', 'title': 'All Chats', 'icon': 'i-chats', 'kind': Folder.Kind.SYSTEM},
    {'slug': 'bots', 'title': 'Bots', 'icon': 'i-bot', 'kind': Folder.Kind.SYSTEM},
    {'slug': 'edit', 'title': 'Edit', 'icon': 'i-pencil', 'kind': Folder.Kind.SYSTEM},
]


def notify_message_created(chat, sender_id, message_data):
    """Yangi xabar haqida chat a'zolarini global kanal (`user_<id>`) orqali ogohlantirish."""
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    layer = get_channel_layer()
    if layer is None:
        return
    for mid in chat.members.exclude(id=sender_id).values_list('id', flat=True):
        async_to_sync(layer.group_send)(
            f'user_{mid}',
            {
                'type': 'notification',
                'payload': {
                    'event': 'message.new',
                    'chat_id': chat.id,
                    'message': message_data,
                },
            },
        )


def broadcast_message_deleted(message):
    """Xabar o'chirilganda ochiq chat oynalari va a'zolar global kanallarini yangilaydi."""
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    layer = get_channel_layer()
    if layer is None:
        return
    data = MessageSerializer(message).data
    async_to_sync(layer.group_send)(
        f'chat_{message.chat_id}', {'type': 'chat.message', 'payload': data}
    )
    notify_message_created(message.chat, message.sender_id, data)


def notify_chat_deleted(chat):
    """Chat/kanal o'chirilganda barcha a'zolar ro'yxatdan olib tashlashi uchun ogohlantirish."""
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    layer = get_channel_layer()
    if layer is None:
        return
    for mid in chat.members.values_list('id', flat=True):
        async_to_sync(layer.group_send)(
            f'user_{mid}',
            {
                'type': 'notification',
                'payload': {'event': 'chat.deleted', 'chat_id': chat.id},
            },
        )


class UploadView(APIView):
    """
    POST /api/uploads/  (multipart: file=..., kind=image|video|audio|voice|file)

    Rasm / video / ovoz yuklaydi va Attachment obyektini qaytaradi:
        {id, kind, url, file_name, mime_type, size, width, height, ...}
    Keyin shu id xabarga biriktiriladi: WS message.create {attachment_id: id}
    yoki REST POST /api/chats/{id}/messages/ {attachment: id}.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        uploaded = request.FILES.get('file')
        if not uploaded:
            return Response(
                {'file': ['Fayl tanlanmadi.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        kind = request.data.get('kind')
        if kind not in Attachment.Kind.values:
            kind = Attachment.Kind.FILE

        name = getattr(uploaded, 'name', '') or 'fayl'
        size = uploaded.size or 0
        try:
            uploaded.seek(0)
            raw = uploaded.read() if size and size < 10 * 1024 * 1024 else b''
            uploaded.seek(0)
        except Exception:
            raw = b''
        attachment = Attachment(
            kind=kind,
            file=uploaded,
            file_name=name,
            mime_type=getattr(uploaded, 'content_type', '') or '',
            size=size,
        )
        if kind == Attachment.Kind.IMAGE:
            try:
                # PIL nusxani o'zi yopadi, asl `uploaded` yopilmaydi.
                from io import BytesIO

                from PIL import Image as PILImage

                img = PILImage.open(BytesIO(raw or b''))
                attachment.width, attachment.height = img.size
                img.close()
                uploaded.seek(0)
            except Exception:
                uploaded.seek(0)
        attachment.save()
        return Response(
            AttachmentSerializer(attachment, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class CallViewSet(viewsets.ModelViewSet):
    """
    Qo'ng'iroq tarixi.

    POST   /api/calls/              — boshlangan qo'ng'iroqni yozib olish
    PATCH  /api/calls/{id}/         — status / duration ni yangilash
    GET    /api/calls/              — tarix
    """

    serializer_class = CallSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    http_method_names = ['get', 'post', 'patch']

    def get_queryset(self):
        return Call.objects.filter(
            chat__members=self.request.user
        ).select_related('chat', 'initiator')

    def perform_create(self, serializer):
        serializer.save(initiator=self.request.user)


class FolderViewSet(viewsets.ModelViewSet):
    """
    Sidebar bo'limlari.

    GET    /api/folders/           — mening papkalarim (tizimlari birinchi bo'lib)
    POST   /api/folders/           — yangi papka
    PATCH  /api/folders/{id}/      — nom / ikonka / rang
    DELETE /api/folders/{id}/      — o'chirish (chatlar folder=None bo'ladi)
    POST   /api/folders/reorder/   — tartibni saqlash
    """

    serializer_class = FolderSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        return Folder.objects.filter(owner=self.request.user)

    def list(self, request, *args, **kwargs):
        """Tizim papkalari har doim birinchi qatorda turadi."""
        return Response(FolderSerializer(self.get_queryset(), many=True).data)

    def perform_create(self, serializer):
        base = serializer.validated_data.get('title', 'chat')
        slug = self.unique_slug(base)
        serializer.save(owner=self.request.user, slug=slug)

    def unique_slug(self, title):
        from django.utils.text import slugify

        base = slugify(title)[:36] or 'folder'
        slug, n = base, 2
        while Folder.objects.filter(owner=self.request.user, slug=slug).exists():
            slug = f'{base}-{n}'
            n += 1
        return slug

    def perform_destroy(self, instance):
        if instance.kind == Folder.Kind.SYSTEM:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Tizim papkasini o'chirib bo'lmaydi.")
        instance.delete()

    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """Body: {"order": [3, 1, 7]} — papkalar id bo'yicha tartibi."""
        order = request.data.get('order')
        if not isinstance(order, list):
            return Response(
                {'order': ['Kamida bitta id yuboring.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        own = set(self.get_queryset().values_list('id', flat=True))
        updated = 0
        for position, folder_id in enumerate(order):
            if folder_id in own:
                Folder.objects.filter(pk=folder_id).update(position=position)
                updated += 1
        return Response({'updated': updated})


class ChatViewSet(viewsets.ModelViewSet):
    """
    GET    /api/chats/              — mening chatlarim
    POST   /api/chats/              — yangi chat (private yoki group)
    GET    /api/chats/{id}/         — bitta chat
    PATCH  /api/chats/{id}/         — chat nomini o'zgartirish (faqat admin)
    DELETE /api/chats/{id}/         — chatni o'chirish (faqat admin)
    GET    /api/chats/{id}/messages/— xabarlar (pagination)
    POST   /api/chats/{id}/messages/— xabar yuborish
    GET    /api/chats/{id}/members/ — a'zolar
    POST   /api/chats/{id}/members/ — a'zo qo'shish
    DELETE /api/chats/{id}/members/{user_id}/ — a'zoni chiqarish
    POST   /api/chats/{id}/read/    — chatni o'qilgan deb belgilash
    """

    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated, IsChatMember]

    def get_queryset(self):
        queryset = (
            Chat.objects.filter(members=self.request.user)
            .select_related('created_by', 'folder', 'pinned_message')
            .prefetch_related('members', 'messages', 'messages__sender')
            .distinct()
        )
        params = self.request.query_params

        folder = params.get('folder')
        if folder:
            if folder == 'all':
                pass
            elif folder == 'bots':
                queryset = queryset.filter(is_bot=True)
            elif folder == 'edit':
                pass
            else:
                queryset = queryset.filter(folder__slug=folder)

        if params.get('favorite') == 'true':
            queryset = queryset.filter(is_favorite=True)
        if params.get('unread') == 'true':
            queryset = queryset.filter(
                messages__is_read=False, messages__sender=self.request.user
            ).exclude(messages__sender=self.request.user).distinct()
        if params.get('channel') == 'true':
            queryset = queryset.filter(is_channel=True)

        search = (params.get('search') or '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(members__username__icontains=search)
                | Q(messages__content__icontains=search)
            ).distinct()

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['user'] = self.request.user
        return context

    def perform_update(self, serializer):
        member = ChatMember.objects.filter(chat=serializer.instance, user=self.request.user).first()
        if not member or member.role != ChatMember.Role.ADMIN:
            raise PermissionDenied('Faqat chat admini o\'zgartira oladi.')
        serializer.save()

    def perform_destroy(self, instance):
        member = ChatMember.objects.filter(chat=instance, user=self.request.user).first()
        if not member or member.role != ChatMember.Role.ADMIN:
            raise PermissionDenied('Faqat chat admini o\'chira oladi.')
        notify_chat_deleted(instance)
        instance.delete()

    @action(detail=True, methods=['get', 'post'], url_path='members')
    def members(self, request, pk=None):
        chat = self.get_object()
        if request.method == 'GET':
            qs = ChatMember.objects.filter(chat=chat).select_related('user')
            return Response(ChatMemberSerializer(qs, many=True).data)

        user_ids = request.data.get('user_ids') or []
        if not isinstance(user_ids, list) or not user_ids:
            return Response(
                {'user_ids': ['Kamida bitta user_id yuboring.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.contrib.auth import get_user_model

        users = get_user_model().objects.filter(pk__in=user_ids)
        existing_ids = set(chat.members.values_list('id', flat=True))
        added = ChatMember.objects.bulk_create(
            [
                ChatMember(chat=chat, user_id=user.pk)
                for user in users
                if user.pk not in existing_ids
            ]
        )
        if not added:
            return Response({'detail': 'Ular allaqachon a\'zo.'}, status=status.HTTP_200_OK)
        return Response(
            ChatMemberSerializer(ChatMember.objects.filter(chat=chat), many=True).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['delete'], url_path=r'members/(?P<user_id>\d+)')
    def remove_member(self, request, pk=None, user_id=None):
        chat = self.get_object()
        if int(user_id) == request.user.pk:
            return Response(
                {'detail': 'O\'zingizni chiqara olmaysiz.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        deleted, _ = ChatMember.objects.filter(chat=chat, user_id=user_id).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get', 'post'], url_path='messages')
    def messages(self, request, pk=None):
        chat = self.get_object()
        queryset = chat.messages.select_related('sender', 'reply_to').prefetch_related(
            'reactions__user', 'read_receipts__user'
        )

        if request.method == 'GET':
            queryset = self._filter_messages(queryset, request.query_params)
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = MessageSerializer(page, many=True, context=self.get_serializer_context())
                return self.get_paginated_response(serializer.data)
            return Response(MessageSerializer(queryset, many=True, context=self.get_serializer_context()).data)

        serializer = MessageSerializer(
            data=request.data, context={**self.get_serializer_context(), 'chat': chat}
        )
        serializer.is_valid(raise_exception=True)
        message = serializer.save(chat=chat, sender=request.user)
        data = MessageSerializer(message, context=self.get_serializer_context()).data
        notify_message_created(chat, request.user.pk, data)
        return Response(data, status=status.HTTP_201_CREATED)

    def _filter_messages(self, queryset, params):
        search = params.get('search')
        if search:
            queryset = queryset.filter(content__icontains=search)
        if params.get('unread') == 'true':
            queryset = queryset.filter(is_read=False).exclude(sender=self.request.user)
        before = params.get('before')
        if before:
            queryset = queryset.filter(id__lt=before)
        return queryset

    @action(detail=True, methods=['post'], url_path='read')
    def mark_chat_read(self, request, pk=None):
        """Chatdagi barcha xabarlarni o'qilgan deb belgilash."""
        chat = self.get_object()
        with transaction.atomic():
            updated = Message.objects.filter(
                chat=chat, is_read=False
            ).exclude(sender=request.user).update(is_read=True)
            member = ChatMember.objects.filter(chat=chat, user=request.user).first()
            last = chat.messages.order_by('-created_at').first()
            if member and last:
                member.last_read_message = last
                member.save(update_fields=['last_read_message'])
        return Response({'marked_read': updated}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post', 'delete'], url_path='pin')
    def pin(self, request, pk=None):
        """POST {message_id} — xabarni yopish. DELETE — yopishni olib tashlash."""
        chat = self.get_object()
        if request.method == 'DELETE':
            chat.pinned_message = None
            chat.is_pinned = False
            chat.save(update_fields=['pinned_message', 'is_pinned'])
            return Response({'is_pinned': False})

        message_id = request.data.get('message_id')
        message = Message.objects.filter(pk=message_id, chat=chat).first()
        if not message:
            return Response(
                {'message_id': ['Xabar bu chatga tegishli emas.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        chat.pinned_message = message
        chat.is_pinned = True
        chat.save(update_fields=['pinned_message', 'is_pinned'])
        return Response({'is_pinned': True, 'message_id': message.id})

    @action(detail=True, methods=['post'], url_path='typing')
    def typing(self, request, pk=None):
        """
        WebSocket ishlamasa zaxira sifatida. Kelganda broadcast qilinadi:
        `channels` `chat_typing` eventini yuboradi.
        """
        self.get_object()
        is_typing = bool(request.data.get('is_typing', True))
        if is_typing:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer

            async_to_sync(get_channel_layer().group_send)(
                f'chat_{pk}',
                {
                    'type': 'chat.typing',
                    'payload': {
                        'user_id': request.user.pk,
                        'username': request.user.username,
                        'is_typing': True,
                    },
                },
            )
        return Response({'is_typing': is_typing})


class MessageViewSet(viewsets.GenericViewSet):
    """
    GET    /api/messages/            — barcha xabarlarim (?chat=)
    GET    /api/messages/{id}/       — bitta xabar
    PATCH  /api/messages/{id}/       — tahrirlash
    DELETE /api/messages/{id}/       — o'chirish (soft delete)
    POST   /api/messages/{id}/read/  — o'qildi deb belgilash
    POST   /api/messages/{id}/react/ — reaction qo'shish/o'chirish
    """

    permission_classes = [IsAuthenticated, IsChatMember, IsMessageOwnerOrAdmin]

    def get_queryset(self):
        return Message.objects.filter(
            chat__members=self.request.user
        ).select_related('chat', 'sender')

    def _message(self, pk):
        return get_object_or_404(self.get_queryset(), pk=pk)

    def list(self, request):
        queryset = self.get_queryset()
        chat_id = request.query_params.get('chat')
        if chat_id:
            queryset = queryset.filter(chat_id=chat_id)
        queryset = queryset.prefetch_related(
            'reactions__user', 'read_receipts__user'
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(MessageSerializer(page, many=True).data)
        return Response(MessageSerializer(queryset, many=True).data)

    def retrieve(self, request, pk=None):
        return Response(MessageSerializer(self._message(pk)).data)

    def partial_update(self, request, pk=None):
        message = self._message(pk)
        self.check_object_permissions(request, message)
        serializer = MessageSerializer(
            message, data=request.data, partial=True, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        message = serializer.save(is_edited=True, updated_at=timezone.now())
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        message = self._message(pk)
        self.check_object_permissions(request, message)
        message.is_deleted = True
        message.content = ''
        message.save(update_fields=['is_deleted', 'content', 'updated_at'])
        broadcast_message_deleted(message)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        message = self._message(pk)
        receipt, created = ReadReceipt.objects.get_or_create(message=message, user=request.user)
        with transaction.atomic():
            Message.objects.filter(chat=message.chat, is_read=False).update(is_read=True)
            member = ChatMember.objects.filter(
                chat=message.chat, user=request.user
            ).first()
            if member:
                member.last_read_message = message
                member.save(update_fields=['last_read_message'])
        return Response(
            {
                'is_read': True,
                'read_at': receipt.read_at,
                'created': created,
            }
        )

    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        message = self._message(pk)
        kind = request.data.get('kind')
        if kind not in Reaction.Kind.values:
            return Response(
                {'kind': [f"Noto'g'ri tur. Tanlash mumkin: {Reaction.Kind.values}"]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reaction, created = Reaction.objects.get_or_create(
            message=message, user=request.user, defaults={'kind': kind}
        )
        if not created and reaction.kind == kind:
            reaction.delete()
            created = False
        else:
            reaction.kind = kind
            reaction.save(update_fields=['kind'])
        return Response(
            {
                'created': created,
                'reactions': ReactionSerializer(
                    Reaction.objects.filter(message=message), many=True
                ).data,
            }
        )
