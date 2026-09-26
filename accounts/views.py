from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.models import Account, Contact, Event, UserSettings
from accounts.serializers import (
    AccountSerializer,
    ContactSerializer,
    EventSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
    UserSettingsSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ — ro'yxatdan o'tish, tokenlar bilan birga."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user.last_seen = timezone.now()
        user.save(update_fields=['last_seen'])
        LoginSerializer.ensure_account(user)

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'account_id': Account.objects.filter(user=user).first().id,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ — username yoki email bilan kirish."""

    serializer_class = LoginSerializer
    permission_classes = [AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/users/me/ — o'z profilim."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class AccountViewSet(viewsets.ModelViewSet):
    """
    Sidebar'dagi account switcher.

    GET    /api/accounts/       — barcha login slotlari
    POST   /api/accounts/       — yangi slot
    PATCH  /api/accounts/{id}/  — nom / tartib
    DELETE /api/accounts/{id}/  — slotni o'chirish (User o'chirilmaydi)
    POST   /api/accounts/{id}/activate/
    """

    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None          # frontend `ACCOUNTS` massivini kutadi
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user).select_related('user')

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Slotni sidebar'da birinchi o'ringa suradi."""
        account = self.get_object()
        first = self.get_queryset().order_by('slot_order', 'id').first()
        if first and first.pk != account.pk:
            account.slot_order, first.slot_order = first.slot_order, account.slot_order
            account.save(update_fields=['slot_order'])
            first.save(update_fields=['slot_order'])
        return Response(AccountSerializer(account, context={'request': request}).data)


class UserSettingsView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/settings/me/ — Night Mode, accent, Enter bilan yuborish."""

    serializer_class = UserSettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj, _ = UserSettings.objects.get_or_create(user=self.request.user)
        return obj


class ContactViewSet(viewsets.ModelViewSet):
    """GET/POST /api/contacts/ — kontaktlar ro'yxati."""

    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        return Contact.objects.filter(owner=self.request.user).select_related('user')


class EventViewSet(viewsets.ModelViewSet):
    """
    Tug'ilgan kun banner'i.

    GET /api/events/?month=8&day=26  — bugungi bayramlar
    """

    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        qs = Event.objects.filter(owner=self.request.user)
        params = self.request.query_params
        try:
            month = int(params.get('month', 0))
            day = int(params.get('day', 0))
        except (TypeError, ValueError):
            month = day = 0

        if 1 <= month <= 12 and 1 <= day <= 31:
            # Yil muhim emas - faqat oy va kun.
            # `__month`/`__day` Django'ning o'z lookup'lari: SQLite'da `strftime`,
            # PostgreSQL'da `EXTRACT` ga kompilyatsiya qilinadi. Xom
            # `EXTRACT(MONTH FROM date)` SQL'i SQLite'da OperationalError beradi.
            qs = qs.filter(date__month=month, date__day=day)
        return qs.order_by('date')


class LogoutView(APIView):
    """POST /api/auth/logout/ — refresh tokenni qora ro'yxatga solish."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get('refresh')
        if not refresh:
            return Response(
                {'detail': "`refresh` maydoni kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh).blacklist()
        except Exception:
            return Response(
                {'detail': 'Token yaroqsiz yoki allaqachon bekor qilingan.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        user.is_online = False
        user.last_seen = timezone.now()
        user.save(update_fields=['is_online', 'last_seen'])
        return Response(status=status.HTTP_205_RESET_CONTENT)


class UserListView(generics.ListAPIView):
    """GET /api/users/ — foydalanuvchilarni qidirish (chat boshlash uchun)."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = User.objects.filter(is_active=True)
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(username__icontains=search) | Q(email__icontains=search)
            )
        return qs.distinct().order_by('username')
