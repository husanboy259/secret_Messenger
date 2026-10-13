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

from chats.models import (
    Attachment,
    Call,
    Chat,
    ChatBan,
    ChatMember,
    Folder,
    JoinRequest,
    Message,
    ReadReceipt,
    Reaction,
)
from chats.permissions import IsChatMember, IsMessageOwnerOrAdmin
from chats.serializers import (
    AttachmentSerializer,
    CallSerializer,
    ChatBanSerializer,
    ChatMemberSerializer,
    ChatSerializer,
    FolderSerializer,
    JoinRequestSerializer,
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


def notify_chat_updated(chat, event='members.updated', extra=None):
    """A'zolik/admin rol o'zgarishini ochiq oyna (chat) va barcha a'zolarga realtime yuboradi."""
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    layer = get_channel_layer()
    if layer is None:
        return
    payload = {'event': event, 'chat_id': chat.id}
    if extra:
        payload.update(extra)
    async_to_sync(layer.group_send)(
        f'chat_{chat.id}', {'type': 'chat.updated', 'payload': payload}
    )
    for mid in chat.members.values_list('id', flat=True):
        async_to_sync(layer.group_send)(
            f'user_{mid}',
            {
                'type': 'notification',
                'payload': {'event': 'chat.updated', 'chat_id': chat.id},
            },
        )


def notify_user(user_id, payload):
    """Bitta foydalanuvchiga realtime event yuborish (join/accept/reject uchun)."""
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(
        f'user_{user_id}', {'type': 'notification', 'payload': payload}
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
                messages__is_read=False,
                messages__is_deleted=False,
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

    def list(self, request, *args, **kwargs):
        # Har kim (eski va yangi foydalanuvchi) o'z support bot chatini ko'radi.
        from chats.bot import ensure_support_chat

        ensure_support_chat(request.user)
        return super().list(request, *args, **kwargs)

    def _require_admin(self, chat, user, message='Faqat adminlar buni qila oladi.'):
        is_admin = ChatMember.objects.filter(
            chat=chat, user=user, role=ChatMember.Role.ADMIN
        ).exists()
        if not is_admin:
            raise PermissionDenied(message)

    def _ensure_can_modify(self, instance):
        member = ChatMember.objects.filter(chat=instance, user=self.request.user).first()
        if not member or member.role != ChatMember.Role.ADMIN:
            raise PermissionDenied("Faqat chat admini o'zgartira oladi.")

    def update(self, request, *args, **kwargs):
        # Adminlikni validatsiyadan oldin tekshiramiz (403 ustuvor bo'lsin).
        self._ensure_can_modify(self.get_object())
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self._ensure_can_modify(self.get_object())
        return super().partial_update(request, *args, **kwargs)

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

        # Guruh/kanalga a'zo qo'shish faqat adminlar ishi (1:1 da ikkalasi admin).
        if chat.type == Chat.Type.GROUP:
            self._require_admin(chat, request.user)

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
                ChatMember(
                    chat=chat,
                    user_id=user.pk,
                    role=ChatMember.Role.ADMIN
                    if request.data.get('role') == ChatMember.Role.ADMIN
                    else ChatMember.Role.MEMBER,
                )
                for user in users
                if user.pk not in existing_ids
            ]
        )
        notify_chat_updated(chat, 'members.updated')
        if not added:
            return Response({'detail': 'Ular allaqachon a\'zo.'}, status=status.HTTP_200_OK)
        return Response(
            ChatMemberSerializer(
                ChatMember.objects.filter(chat=chat).select_related('user'), many=True
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['delete'], url_path=r'members/(?P<user_id>\d+)')
    def remove_member(self, request, pk=None, user_id=None):
        chat = self.get_object()
        if chat.type == Chat.Type.GROUP:
            self._require_admin(chat, request.user)
        if int(user_id) == chat.created_by_id:
            return Response(
                {'detail': 'Chat egasini chiqarib bo\'lmaydi.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if int(user_id) == request.user.pk:
            return Response(
                {'detail': 'O\'zingizni chiqara olmaysiz.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        deleted, _ = ChatMember.objects.filter(chat=chat, user_id=user_id).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        notify_chat_updated(chat, 'members.updated')
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['patch'],
        url_path=r'members/(?P<user_id>\d+)/role',
    )
    def set_member_role(self, request, pk=None, user_id=None):
        """PATCH {role: 'admin'|'member'} — admin qo'shish/cheklash. Faqat admin.  Egani o'zgarmaydi."""
        chat = self.get_object()
        self._require_admin(chat, request.user)
        role = (request.data.get('role') or '').strip().lower()
        if role not in (ChatMember.Role.ADMIN, ChatMember.Role.MEMBER):
            return Response(
                {'role': "'admin' yoki 'member' kiring."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        member = ChatMember.objects.filter(chat=chat, user_id=user_id).first()
        if not member:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if member.user_id == chat.created_by_id:
            return Response(
                {'detail': "Channel/chat egasining rolini o'zgartirib bo'lmaydi."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        member.role = role
        member.save(update_fields=['role'])
        notify_chat_updated(
            chat, 'members.updated', {'user_id': int(user_id), 'role': role}
        )
        return Response(
            ChatMemberSerializer(member, context=self.get_serializer_context()).data
        )

    # ── join / invite ───────────────────────────────────────────────────────
    @action(detail=True, methods=['get'], url_path='invite')
    def invite(self, request, pk=None):
        """GET /api/chats/{id}/invite/ — guruh/kanal join-linkini qaytaradi."""
        chat = self.get_object()
        if chat.type != Chat.Type.GROUP:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        base = request.build_absolute_uri('/')
        code = chat.ensure_invite_code()
        return Response({'invite_code': code, 'url': f'{base}join.html?code={code}'})

    @action(detail=False, methods=['get'], url_path='by-invite/(?P<code>[^/.]+)')
    def by_invite(self, request, code=None):
        """GET /api/chats/by-invite/{code}/ — join sahifasi uchun ochiq ma'lumot."""
        chat = Chat.objects.filter(invite_code=code).first()
        if not chat or chat.type != Chat.Type.GROUP:
            return Response(status=status.HTTP_404_NOT_FOUND)
        member_ids = set(chat.members.values_list('id', flat=True))
        joined = request.user.pk in member_ids
        pending = None
        if not joined and request.user.is_authenticated:
            req = JoinRequest.objects.filter(chat=chat, user=request.user).first()
            pending = req.status if req else None
        return Response({
            'id': chat.id,
            'type': chat.type,
            'name': chat.name,
            'avatar': chat.avatar,
            'username': chat.username,
            'about': chat.about,
            'is_channel': chat.is_channel,
            'is_public': chat.is_public,
            'member_count': len(member_ids),
            'joined': joined,
            'request': pending,
        })

    @action(detail=False, methods=['get'], url_path='discover')
    def discover(self, request, pk=None):
        """GET /api/chats/discover/?q= — ommaviy guruh/kanallarni @username/ism bo'yicha qidirish."""
        q = (request.query_params.get('q') or '').strip().lstrip('@')
        qs = Chat.objects.filter(is_public=True, type=Chat.Type.GROUP)
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(name__icontains=q))
        return Response([
            {
                'id': c.id,
                'name': c.name,
                'avatar': c.avatar,
                'username': c.username,
                'about': c.about,
                'is_channel': c.is_channel,
                'member_count': c.members.count(),
            }
            for c in qs.exclude(created_by=request.user)[:40]
        ])

    @action(detail=True, methods=['post'], url_path='join')
    def join(self, request, pk=None):
        """POST /api/chats/{id}/join/ — ochiq guruhga qo'shilish yoki xususiyga so'rov yuborish.

        A'zo bo'lmagan foydalanuvchi ham chaqira oladi — shuning uchun
        a'zolik bo'yicha filtrlaydigan `self.get_object()` emas, to'g'ridan-to'g'ri
        `Chat`dan olamiz (aks holda 404 bo'lardi, join.html ishlamasdi).
        """
        chat = Chat.objects.filter(pk=pk).first()
        if not chat:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if chat.type != Chat.Type.GROUP:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if ChatBan.objects.filter(chat=chat, user=request.user).exists():
            return Response(
                {'detail': "Siz bu guruhdan ban qilingansiz."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if chat.members.filter(pk=request.user.pk).exists():
            return Response({'joined': True, 'request': None})
        if chat.is_public:
            ChatMember.objects.get_or_create(
                chat=chat, user=request.user, defaults={'role': ChatMember.Role.MEMBER}
            )
            notify_chat_updated(chat, 'members.updated', {'user_id': request.user.pk})
            return Response({'joined': True, 'request': None})
        req, created = JoinRequest.objects.get_or_create(
            chat=chat, user=request.user, defaults={'status': JoinRequest.Status.PENDING}
        )
        if created:
            self._notify_admins_join(chat)
        return Response({'joined': False, 'request': req.status})

    def _notify_admins_join(self, chat):
        """Adminlarga yangi qo'shilish so'rovi haqida realtime xabar."""
        for admin_id in ChatMember.objects.filter(
            chat=chat, role=ChatMember.Role.ADMIN
        ).values_list('user_id', flat=True):
            notify_user(admin_id, {'event': 'join.request', 'chat_id': chat.id})

    @action(detail=True, methods=['get'], url_path='join-requests')
    def join_requests(self, request, pk=None):
        """GET /api/chats/{id}/join-requests/ — (admin) kutilayotgan so'rovlar."""
        chat = self.get_object()
        self._require_admin(chat, request.user)
        qs = JoinRequest.objects.filter(chat=chat, status=JoinRequest.Status.PENDING)
        return Response(JoinRequestSerializer(qs, many=True).data)

    @action(
        detail=True,
        methods=['post'],
        url_path=r'join-requests/(?P<rid>\d+)/(?P<answer>accept|reject)',
    )
    def answer_join_request(self, request, pk=None, rid=None, answer=None):
        """POST /api/chats/{id}/join-requests/{rid}/accept|reject/ — (admin) so'rovni hal qilish."""
        chat = self.get_object()
        self._require_admin(chat, request.user)
        req = JoinRequest.objects.filter(pk=rid, chat=chat).first()
        if not req or req.status != JoinRequest.Status.PENDING:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if answer == 'accept':
            ChatMember.objects.get_or_create(
                chat=chat, user=req.user, defaults={'role': ChatMember.Role.MEMBER}
            )
            req.status = JoinRequest.Status.APPROVED
            notify_user(req.user_id, {
                'event': 'join.accepted',
                'chat_id': chat.id,
                'chat': ChatSerializer(chat, context=self.get_serializer_context()).data,
            })
            notify_chat_updated(chat, 'members.updated', {'user_id': req.user_id})
        else:
            req.status = JoinRequest.Status.REJECTED
            notify_user(req.user_id, {
                'event': 'join.rejected',
                'chat_id': chat.id,
                'chat': ChatSerializer(chat, context=self.get_serializer_context()).data,
            })
        req.save(update_fields=['status'])
        return Response({'status': req.status})

    # ── ban / mute ──────────────────────────────────────────────────────────
    def _managed_member(self, chat, user_id):
        member = ChatMember.objects.filter(chat=chat, user_id=user_id).first()
        if not member:
            raise PermissionDenied('Bu foydalanuvchi guruhda emas.')
        if member.user_id == chat.created_by_id:
            raise PermissionDenied('Chat egasini cheklab bo\'lmaydi.')
        if member.user_id == self.request.user.pk:
            raise PermissionDenied('O\'zingizni cheklay olmaysiz.')
        return member

    @action(detail=True, methods=['post', 'delete'], url_path=r'members/(?P<user_id>\d+)/ban')
    def ban_member(self, request, pk=None, user_id=None):
        """POST   — (owner/admin) a'zoni chiqarish + ban tarixiga yozish.
        DELETE — (owner/admin) ban bekor qilish."""
        chat = self.get_object()
        self._require_admin(chat, request.user)
        if request.method == 'DELETE':
            deleted, _ = ChatBan.objects.filter(chat=chat, user_id=user_id).delete()
            if not deleted:
                return Response(status=status.HTTP_404_NOT_FOUND)
            return Response(status=status.HTTP_204_NO_CONTENT)
        if int(user_id) == chat.created_by_id:
            return Response(
                {'detail': 'Chat egasini chiqarib bo\'lmaydi.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ChatMember.objects.filter(chat=chat, user_id=user_id).delete()
        ChatBan.objects.update_or_create(
            chat=chat,
            user_id=user_id,
            defaults={
                'banned_by': request.user,
                'reason': (request.data.get('reason') or '').strip(),
            },
        )
        notify_chat_updated(chat, 'members.updated', {'user_id': int(user_id), 'banned': True})
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path=r'members/(?P<user_id>\d+)/mute')
    def mute_member(self, request, pk=None, user_id=None):
        """POST /api/chats/{id}/members/{uid}/mute/ — (owner/admin) yozishni vaqtinchalik to'xtatish.
        Body: {minutes: N} — ko'rsatilmasa doimiy."""
        chat = self.get_object()
        self._require_admin(chat, request.user)
        member = self._managed_member(chat, user_id)
        minutes = int(request.data.get('minutes') or 0)
        if minutes and minutes > 0:
            member.muted_until = timezone.now() + timezone.timedelta(minutes=minutes)
            member.is_muted = False
        else:
            member.muted_until = None
            member.is_muted = True
        member.save(update_fields=['is_muted', 'muted_until'])
        notify_chat_updated(chat, 'members.updated', {'user_id': int(user_id), 'muted': True})
        return Response(
            ChatMemberSerializer(member, context=self.get_serializer_context()).data
        )

    @action(detail=True, methods=['post'], url_path=r'members/(?P<user_id>\d+)/unmute')
    def unmute_member(self, request, pk=None, user_id=None):
        """POST /api/chats/{id}/members/{uid}/unmute/ — (owner/admin) mute bekor."""
        chat = self.get_object()
        self._require_admin(chat, request.user)
        member = self._managed_member(chat, user_id)
        member.is_muted = False
        member.muted_until = None
        member.save(update_fields=['is_muted', 'muted_until'])
        notify_chat_updated(chat, 'members.updated', {'user_id': int(user_id), 'muted': False})
        return Response(
            ChatMemberSerializer(member, context=self.get_serializer_context()).data
        )

    # ── banlarni ro'yxatlash (manage panel uchun) ──────────────────────────
    @action(detail=True, methods=['get'], url_path='bans')
    def bans(self, request, pk=None):
        chat = self.get_object()
        self._require_admin(chat, request.user)
        return Response(
            ChatBanSerializer(
                ChatBan.objects.filter(chat=chat).select_related('user', 'banned_by'),
                many=True,
            ).data
        )

    @action(detail=True, methods=['post'], url_path='leave')
    def leave(self, request, pk=None):
        """POST /api/chats/{id}/leave/ — guruhdan chiqish (egoa chiqa olmaydi)."""
        chat = self.get_object()
        if chat.type != Chat.Type.GROUP:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if chat.created_by_id == request.user.pk:
            return Response(
                {'detail': 'Ega guruhdan chiqib bo\'lmaydi.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        deleted, _ = ChatMember.objects.filter(
            chat=chat, user_id=request.user.pk
        ).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        notify_chat_updated(chat, 'members.updated', {'user_id': request.user.pk})
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
        if not chat.can_post(request.user):
            raise PermissionDenied('Kanalga faqat adminlar yoza oladi.')
        if chat.is_muted_user(request.user):
            raise PermissionDenied('Siz bu chatda mute qilingansiz — yozolmaysiz.')
        message = serializer.save(chat=chat, sender=request.user)
        data = MessageSerializer(message, context=self.get_serializer_context()).data
        notify_message_created(chat, request.user.pk, data)
        from chats.bot import route_bot_reply

        route_bot_reply(chat, message)
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
