from rest_framework import serializers

from accounts.serializers import UserSerializer
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


class AttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            'id',
            'kind',
            'url',
            'file_name',
            'mime_type',
            'size',
            'width',
            'height',
            'duration',
            'thumbnail',
            'created_at',
        ]
        read_only_fields = fields

    def get_url(self, obj):
        if not obj.file:
            return ''
        request = self.context.get('request')
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url


class FolderSerializer(serializers.ModelSerializer):
    chat_count = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = [
            'id',
            'slug',
            'title',
            'kind',
            'icon',
            'position',
            'accent',
            'chat_count',
        ]
        read_only_fields = ['id', 'slug', 'kind', 'chat_count']

    def get_chat_count(self, obj):
        return obj.chats.count()


class ReactionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Reaction
        fields = ['id', 'user', 'kind']


class ReadReceiptSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ReadReceipt
        fields = ['id', 'user', 'read_at']


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    reply_to = serializers.PrimaryKeyRelatedField(
        queryset=Message.objects.all(),
        allow_null=True,
        required=False,
        help_text='Javoblanayotgan xabar id si.',
    )
    reply_to_detail = serializers.SerializerMethodField()
    attachment = serializers.PrimaryKeyRelatedField(
        queryset=Attachment.objects.all(),
        allow_null=True,
        required=False,
        help_text='Biriktirilgan fayl id si.',
    )
    attachment_detail = AttachmentSerializer(source='attachment', read_only=True)
    reactions = ReactionSerializer(many=True, read_only=True)
    read_by = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id',
            'chat',
            'sender',
            'content',
            'reply_to',
            'reply_to_detail',
            'attachment',
            'attachment_detail',
            'client_id',
            'is_read',
            'is_edited',
            'is_deleted',
            'created_at',
            'updated_at',
            'reactions',
            'read_by',
        ]
        read_only_fields = [
            'id',
            'chat',
            'sender',
            'is_read',
            'is_edited',
            'is_deleted',
            'created_at',
            'updated_at',
            'reactions',
            'read_by',
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        has_text = bool((attrs.get('content') or '').strip())
        has_attachment = attrs.get('attachment') is not None
        if not has_text and not has_attachment:
            raise serializers.ValidationError(
                {'content': "Xabar bo'sh bo'lishi mumkin emas."}
            )
        return attrs

    def get_reply_to_detail(self, obj):
        if not obj.reply_to_id:
            return None
        reply = obj.reply_to
        return {
            'id': reply.id,
            'content': '' if reply.is_deleted else reply.content,
            'sender': UserSerializer(reply.sender).data,
            'attachment': {'kind': reply.attachment.kind} if reply.attachment_id else None,
        }

    def get_read_by(self, obj):
        receipts = obj.read_receipts.select_related('user')[:20]
        return [
            {'id': r.user_id, 'username': r.user.username, 'read_at': r.read_at}
            for r in receipts
        ]

    def validate_content(self, value):
        return value.strip()

    def validate_reply_to(self, value):
        chat = self.context.get('chat') or getattr(self.instance, 'chat', None)
        if value and chat and value.chat_id != chat.id:
            raise serializers.ValidationError(
                'Javoblanayotgan xabar boshqa chatga tegishli.'
            )
        return value


class CallSerializer(serializers.ModelSerializer):
    """Qo'ng'iroq tarixi. Frontend WS orqali signal almashadi,
    bu faqat hisob (log) uchun."""

    initiator = UserSerializer(read_only=True)

    class Meta:
        model = Call
        fields = [
            'id',
            'chat',
            'initiator',
            'kind',
            'status',
            'started_at',
            'duration',
            'created_at',
        ]
        read_only_fields = ['id', 'initiator', 'created_at']


class ChatMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    last_read_message = MessageSerializer(read_only=True)

    class Meta:
        model = ChatMember
        fields = ['id', 'user', 'role', 'joined_at', 'last_read_message']


class ChatSerializer(serializers.ModelSerializer):
    members = UserSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
        help_text='Chatga qo\'shiladigan foydalanuvchi idlari.',
    )
    title = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()
    folder = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.all(),
        allow_null=True,
        required=False,
        help_text='Sidebar papkasi (Folder id si).',
    )
    folder_detail = FolderSerializer(source='folder', read_only=True)

    class Meta:
        model = Chat
        fields = [
            'id',
            'type',
            'name',
            'title',
            'avatar',
            'created_by',
            'members',
            'member_ids',
            'folder',
            'folder_detail',
            'is_channel',
            'is_bot',
            'is_favorite',
            'is_muted',
            'is_pinned',
            'pinned_message',
            'last_message',
            'unread_count',
            'my_role',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'created_by',
            'members',
            'created_at',
        ]

    def get_title(self, obj):
        if obj.name:
            return obj.name
        others = [m for m in obj.members.all() if m.pk != self.context['user'].pk]
        if others:
            return ', '.join(o.display_name or o.username for o in others)
        return 'Bo\'sh suhbat'

    def get_last_message(self, obj):
        message = obj.messages.filter(is_deleted=False).order_by('-created_at').first()
        if not message:
            return None
        return {
            'id': message.id,
            'content': message.content,
            'sender': message.sender.username,
            'created_at': message.created_at,
            'is_read': message.is_read,
        }

    def get_unread_count(self, obj):
        user = self.context['user']
        return (
            obj.messages.filter(is_read=False, is_deleted=False)
            .exclude(sender=user)
            .count()
        )

    def get_my_role(self, obj):
        member = ChatMember.objects.filter(
            chat=obj, user_id=self.context['user'].pk
        ).first()
        return member.role if member else None

    def validate_member_ids(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("Kamida bitta a'zo tanlang.")
        if self.instance and self.instance.type == Chat.Type.PRIVATE and len(value) != 1:
            raise serializers.ValidationError(
                "Shaxsiy chatda faqat bitta suhbatdosh bo'lishi kerak."
            )
        return value

    def validate(self, attrs):
        # Pinned xabar shu chatga tegishli bo'lishi kerak.
        pinned = attrs.get('pinned_message')
        if pinned is not None:
            target_chat = self.instance or pinned.chat
            if pinned.chat_id != target_chat.id:
                raise serializers.ValidationError(
                    {'pinned_message': 'Xabar boshqa chatga tegishli.'}
                )

        if self.instance:
            # PATCH: faqat nom/avatar o'zgaradi, a'zolar va tur emas.
            if 'type' in attrs and attrs['type'] != self.instance.type:
                raise serializers.ValidationError(
                    {'type': 'Chat turini o\'zgartirib bo\'lmaydi.'}
                )
            return attrs

        data_type = attrs.get('type', Chat.Type.PRIVATE)
        if data_type == Chat.Type.GROUP and not attrs.get('name'):
            raise serializers.ValidationError({'name': 'Guruh nomi kerak.'})

        member_ids = attrs.get('member_ids') or []
        requester = self.context['request'].user
        selected = list(member_ids)
        if requester.pk not in selected:
            selected.append(requester.pk)

        if not selected:
            raise serializers.ValidationError({'member_ids': "A'zo tanlanmagan."})
        if len(selected) != len(set(selected)):
            raise serializers.ValidationError({'member_ids': 'A\'zolar takrorlangan.'})

        from django.contrib.auth import get_user_model

        users = get_user_model().objects.filter(pk__in=selected)
        if users.count() != len(set(selected)):
            raise serializers.ValidationError({'member_ids': 'Foydalanuvchi topilmadi.'})

        if data_type == Chat.Type.PRIVATE:
            if users.count() != 2:
                raise serializers.ValidationError(
                    {'member_ids': "Shaxsiy chatda 2 ta foydalanuvchi bo'lishi kerak."}
                )
            existing = (
                Chat.objects.filter(type=Chat.Type.PRIVATE, members__in=users)
                .distinct()
                .count()
            )
            if existing:
                raise serializers.ValidationError(
                    'Bu suhbat allaqachon mavjud.', code='duplicate'
                )

        attrs['member_ids'] = list(users.values_list('id', flat=True))
        return attrs


    def create(self, validated_data):
        member_ids = validated_data.pop('member_ids')
        requester = self.context['request'].user
        members = list(dict.fromkeys([requester.pk, *member_ids]))
        chat = Chat.objects.create(created_by=requester, **validated_data)
        ChatMember.objects.bulk_create(
            [
                ChatMember(
                    chat=chat,
                    user_id=user_id,
                    role=ChatMember.Role.ADMIN if user_id == requester.pk else ChatMember.Role.MEMBER,
                )
                for user_id in members
            ]
        )
        return chat
