from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings

from accounts.models import Account, Contact, Event, UserSettings

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    is_online = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'display_name',
            'bio',
            'avatar',
            'emoji_status',
            'is_online',
            'last_seen',
            'unread_count',
        ]
        read_only_fields = ['id', 'username', 'last_seen', 'unread_count']

    def get_is_online(self, user):
        from chats.models import is_online

        return is_online(user)

    def get_unread_count(self, user):
        from chats.models import unread_count_for

        return unread_count_for(user)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'password',
            'password_confirm',
            'display_name',
        ]
        read_only_fields = ['id']

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Bu email allaqachon ro\'yxatdan o\'tgan.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError(
                {'password_confirm': 'Parollar mos kelmadi.'}
            )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.is_online = True
        user.save()
        return user


class LoginSerializer(TokenObtainPairSerializer):
    """Username yoki email orqali kirish.

    Sorov: {"username": "ali", "password": "..."}
           {"username": "ali@mail.com", "password": "..."}

    `username` maydoni SimpleJWT tomonidan `__init__` da qayta yaratiladi,
    shuning uchun uni required=False qilib o'zgartirib bo'lmaydi — shuning
    uchun bitta maydon ikkalasini ham qabul qiladi.

    Javobga `account_id` qo'shiladi — frontend account switcher uchun
    kalit sifatida ishlatadi (localStorage: `access:<account_id>`).
    """


    username_field = 'username'

    def validate(self, attrs):
        identifier = (attrs.get(self.username_field) or '').strip()
        password = attrs.get('password')

        if not identifier:
            raise serializers.ValidationError(
                {'username': 'Username yoki email kiriting.'},
                code='identifier_required',
            )

        user = User.objects.filter(email__iexact=identifier).first()
        if user is None:
            user = User.objects.filter(username__iexact=identifier).first()

        if user is None:
            raise serializers.ValidationError(
                {'username': 'Bunday foydalanuvchi topilmadi.'},
                code='user_not_found',
            )
        if not user.is_active:
            raise serializers.ValidationError(
                {'username': 'Bu hisob bloklangan.'},
                code='user_inactive',
            )
        if not user.check_password(password):
            raise serializers.ValidationError(
                {'password': "Parol noto'g'ri."},
                code='wrong_password',
            )

        self.user = user
        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, user)

        account = self.ensure_account(user)
        refresh = self.get_token(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data,
            'account_id': account.id if account else None,
        }

    @staticmethod
    def ensure_account(user):
        """Kirganda avvalgi Account slotini topamiz yoki yaratamiz."""
        account = Account.objects.filter(user=user).order_by('slot_order', 'id').first()
        if account is None:
            last = Account.objects.filter(user=user).order_by('-slot_order').first()
            account = Account.objects.create(
                user=user,
                label=user.display_name or user.username,
                slot_order=(last.slot_order + 1) if last else 0,
            )
        account.last_used_at = timezone.now()
        account.save(update_fields=['last_used_at'])
        return account


class AccountSerializer(serializers.ModelSerializer):
    """Frontend sidebar'dagi account switcher (`ACCOUNTS` massivi)."""

    name = serializers.CharField(source='label', read_only=True)
    sub = serializers.SerializerMethodField()
    emoji = serializers.CharField(source='user.emoji_status', read_only=True)
    avatar = serializers.URLField(source='user.avatar', read_only=True)
    unread = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            'id',
            'name',
            'label',
            'sub',
            'emoji',
            'avatar',
            'unread',
            'is_active',
            'status',
            'slot_order',
            'last_used_at',
            'created_at',
        ]
        read_only_fields = ['id', 'status', 'last_used_at', 'created_at']

    def get_sub(self, obj):
        return obj.user.email or obj.user.username

    def get_unread(self, obj):
        from chats.models import unread_count_for

        return unread_count_for(obj.user)

    def get_is_active(self, obj):
        request = self.context.get('request')
        if not request:
            return False
        return Account.objects.filter(
            user=request.user, status=Account.Status.ACTIVE
        ).order_by('slot_order', 'id').first() == obj


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = [
            'theme',
            'accent',
            'send_on_enter',
            'show_birthday_banner',
            'wallpaper',
            'updated_at',
        ]
        read_only_fields = ['updated_at']


class ContactSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source='user', queryset=User.objects.all(), write_only=True
    )

    class Meta:
        model = Contact
        fields = ['id', 'user', 'user_id', 'nickname', 'is_favorite', 'created_at']
        read_only_fields = ['id', 'created_at']


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'person_name', 'date', 'kind', 'emoji']
        read_only_fields = ['id']
