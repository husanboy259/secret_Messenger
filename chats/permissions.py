from rest_framework.permissions import SAFE_METHODS, BasePermission

from chats.models import Chat, ChatMember


class IsChatMember(BasePermission):
    """Faqat chatning a'zolari kirishi mumkin.

    ViewSet'lar `get_queryset()` da allaqachon `chat__members=request.user`
    filtri bor, shuning uchun begona foydalanuvchi obyektni umuman topa olmaydi
    va 404 oladi (bu 403 dan xavfsizroq — mavjudlik oshkor bo'lmaydi).
    """

    message = "Bu suhbatga a'zo emassiz."

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        chat = obj if hasattr(obj, 'members') else obj.chat
        return chat.members.filter(pk=request.user.pk).exists()


class IsMessageOwnerOrAdmin(BasePermission):
    """Xabarni tahrirlash/o'chirish: yuborgani yoki guruh admini.

    Shaxsiy (private) chatda admin roli ikki teng a'zodan birinikisi bo'lgani
    uchun suhbatdoshning xabarini tahrirlashga yo'l qo'yilmaydi — faqat
    guruhlarda moderatsiya bor.
    """

    message = "Bu xabarni faqat yuborganingiz tahrirlay oladi."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if obj.sender_id == request.user.pk:
            return True
        if obj.chat.type != Chat.Type.GROUP:
            return False
        return ChatMember.objects.filter(
            chat=obj.chat, user=request.user, role=ChatMember.Role.ADMIN
        ).exists()
