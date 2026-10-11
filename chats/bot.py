"""Support / AI bot chat.

Har foydalanuvchi (yangi yoki eski) o'zining 1:1 support chatiga ega bo'ladi
— bu chat oddiy chat kabi ko'rinadi va «Bots» papkasida ham turadi.

AI back-end keyinroq ulanadi (ROADMAP_AI_BOT.md): `route_bot_reply` shu joyda
haqiqiy javob yaratadi.
"""

import logging

logger = logging.getLogger(__name__)

SUPPORT_USERNAME = 'support_bot'
SUPPORT_CHAT_NAME = 'Messger Support'


def get_support_bot():
    from django.contrib.auth import get_user_model

    bot, _ = get_user_model().objects.get_or_create(
        username=SUPPORT_USERNAME,
        defaults={
            'display_name': 'Messger Support',
            'is_active': True,
            'email': '',
        },
    )
    return bot


def ensure_support_chat(user):
    """Foydalanuvchiga biriktirilgan support chatini qaytaradi (kerak bo'lsa yaratadi).

    Ro'yxat yuklanganda ham, ro'yxatdan o'tishda ham chaqiriladi, shuning uchun
    ham eski, ham yangi sign-up qilgan foydalanuvchilar ko'radilar.
    """
    from chats.models import Chat, ChatMember

    bot = get_support_bot()
    chat = (
        Chat.objects.filter(type=Chat.Type.PRIVATE, is_bot=True, members=user)
        .distinct()
        .first()
    )
    if chat is None:
        chat = Chat.objects.create(
            type=Chat.Type.PRIVATE,
            name=SUPPORT_CHAT_NAME,
            is_bot=True,
            created_by=bot,
        )
        ChatMember.objects.bulk_create(
            [
                ChatMember(chat=chat, user=user, role=ChatMember.Role.MEMBER),
                ChatMember(chat=chat, user=bot, role=ChatMember.Role.ADMIN),
            ]
        )
    return chat


def route_bot_reply(chat, message):
    """Support chatga kelgan xabarga javob yaratish hook'i.

    AI ulangandan so'ng shu funksiya:
      1. `chat.is_bot` bo'lsa ishlaydi;
      2. `message.content` (va suhbat konteksti/yangi xabarlar) AI providerga
         yuboriladi;
      3. natija shu chatga xabar sifatida yozilib, realtime broadcast qilinadi.

    Hozircha faqat log yozadi — to'liq yo'riq ROADMAP_AI_BOT.md da.
    """
    if not chat.is_bot:
        return None
    logger.info('Support chat #%s: xabar #%s keldi (AI hook kutmoqda)',
                chat.id, message.id)
    return None