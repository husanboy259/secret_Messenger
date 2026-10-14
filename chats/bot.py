"""Support / AI bot chat.

Har foydalanuvchi (yangi yoki eski) o'zining 1:1 support chatiga ega bo'ladi
— bu chat oddiy chat kabi ko'rinadi va «Bots» papkasida ham turadi.

AI javob OpenAI-compatible API (Google AI Studio/Gemini, OpenRouter) orqali
yaratiladi: `route_bot_reply` hook'i foydalanuvchi xabariga javobni background
thread'da tayyorlab, oddiy `Message` sifatida realtime broadcast qiladi. To'liq
reja — ROADMAP_AI_BOT.md.
"""

import logging
import threading

from django.conf import settings

logger = logging.getLogger(__name__)

# Har chat uchun alohida lock — tez ketma-ket yozilgan xabarlarda bot javoblari
# duplikat bo'lib qolmasligi uchun javob tayyorlash serializatsiya qilinadi.
_reply_locks = {}
_reply_locks_guard = threading.Lock()


def _chat_lock(chat_id):
    with _reply_locks_guard:
        return _reply_locks.setdefault(chat_id, threading.Lock())


SUPPORT_USERNAME = 'support_bot'
SUPPORT_CHAT_NAME = 'Messger Support'

SYSTEM_PROMPT = (
    "Siz Messger ilovasining rasmiy support yordamchisisiz. "
    "Qisqa, aniq va do'stona javob bering. Foydalanuvchi savolini e'tiborga oling, "
    "ilova haqida bilmagan narsangizni o'ylab chiqmang. Noaniq yoki imkonsiz "
    "narsa so'ralsa, halol ayting va kerak bo'lsa operatorga murojaat qilishni "
    "tavsiya qiling."
)


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
    """Support chatga kelgan xabarga realtime AI javob yaratish hook'i.

    WS (`message.create`, ovozli) ham, REST (`/messages` POST) ham shu funksiyani
    chaqiradi. Javob background thread'da tayyorlanadi, shunda foydalanuvchi
    so'rovi bloklanmaydi.
    """
    if not chat.is_bot:
        return None
    if not settings.AI_ENABLED:
        return None
    if message.sender_id == get_support_bot().pk:
        return None  # bot o'z javobiga qayta javob bermaydi
    if not settings.AI_API_KEY:
        logger.warning("AI_ENABLED=True, lekin AI_API_KEY bo'sh — support javobsiz.")
        return None

    threading.Thread(
        target=build_bot_reply,
        args=(chat.id, message.id),
        daemon=True,
        name='ai-support-reply',
    ).start()
    return None


def build_bot_reply(chat_id, message_id):
    """Background thread: kontekstni yig'ib AI'ga yuboradi va natijani chatga yozadi."""
    from django.db import close_old_connections

    close_old_connections()
    try:
        from chats.models import Chat, Message

        chat = Chat.objects.filter(pk=chat_id, is_bot=True).first()
        if chat is None:
            return
        if not Message.objects.filter(pk=message_id, chat_id=chat.id).exists():
            return

        with _chat_lock(chat.id):
            reply = _generate_reply(chat, message_id)
            if reply:
                _publish_bot_message(chat, reply)
    except Exception:
        logger.exception('AI javobni tayyorlashda xato (chat=%s)', chat_id)
    finally:
        close_old_connections()


def _generate_reply(chat, message_id):
    """Suhbat kontekstini yig'ib, AI providerdan javob matnini qaytaradi."""
    from chats.models import Message

    bot = get_support_bot()

    trigger = Message.objects.filter(
        pk=message_id, chat_id=chat.id, is_deleted=False
    ).first()
    if trigger is None or trigger.sender_id == bot.pk:
        return None
    # Tetik xabarga allaqachon javob yozilgan — takror javob yaratmaymiz.
    if Message.objects.filter(
        chat_id=chat.id, sender_id=bot.pk, id__gt=trigger.pk
    ).exists():
        logger.info('AI: bu xabarga allaqachon javob bor (chat=%s)', chat.id)
        return None

    history = list(
        Message.objects.filter(chat_id=chat.id, is_deleted=False)
        .exclude(content='')
        .order_by('-id')[: settings.AI_CONTEXT_MESSAGES]
    )
    history = sorted(history, key=lambda m: m.id)
    if not history:
        return None
    # Oxirgi xabar botnicmi? Unda javob allaqachon qo'yilgan — qayta javob yo'q.
    if history[-1].sender_id == bot.pk:
        logger.info('AI: oxirgi xabar botniki — javob kerak emas (chat=%s)', chat.id)
        return None

    conv = []
    for m in history:
        role = 'assistant' if m.sender_id == bot.pk else 'user'
        if conv and conv[-1]['role'] == role:
            continue
        conv.append({'role': role, 'content': m.content[:4000]})
    while conv and conv[0]['role'] == 'assistant':
        conv.pop(0)
    if not conv:
        return None

    from chats.ai.provider import LLMError, chat_completion

    payload = [{'role': 'system', 'content': SYSTEM_PROMPT}] + conv
    try:
        return chat_completion(payload)
    except LLMError as exc:
        logger.error('AI javob olinmadi (chat=%s, model=%s, base=%s): %s',
                     chat.id, settings.AI_MODEL, settings.AI_BASE_URL, exc)
        if settings.AI_DEBUG:
            return f"AI xato (DEBUG): {exc}"[:500]
        return (
            "Kechirasiz, hozir javob bera olmayapman. "
            "Birozdan so'ng qayta urinib ko'ring."
        )


def _publish_bot_message(chat, text):
    """Bot javobini Message sifatida yozib, realtime broadcast qiladi.

    Ochig' protsedura konsumerlardagi `message.new` oqimiga mos: guruhga ham,
    global kanalga ham yuboriladi — frontend bot javobini oddiy xabar sifatida
    ko'rsatadi.
    """
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    from chats.models import Message
    from chats.serializers import MessageSerializer
    from chats.views import notify_message_created

    bot = get_support_bot()
    msg = Message.objects.create(chat=chat, sender=bot, content=text)
    data = MessageSerializer(msg).data

    layer = get_channel_layer()
    if layer is not None:
        async_to_sync(layer.group_send)(
            f'chat_{chat.id}', {'type': 'chat.message', 'payload': data}
        )
    notify_message_created(chat, bot.id, data)