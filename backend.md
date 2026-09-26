# MESSGER — BACKEND.md

Frontend (`messenger.html` / `messenger.css` / `messenger.js`) tayyor. Uning ichidagi
barcha ma'lumotlar hozircha **mock** (JS ichida yozilgan). Bu fayl shu mocklarni haqiqiy
backend'ga ulash uchun yozilgan.

> Har bir bo'limdagi endpoint jadvali `messenger.js` dagi `CHATS`, `ACCOUNTS`, `ME`
> obyektlariga **1:1** mos keladi. Shu sababli frontend'ni o'zgartirmasdan ulash mumkin.

---

## 📍 0. HOZIRGI HOLAT (nima bor, nima yo'q)

| Qism | Holat |
|---|---|
| `config/settings.py` | ✅ DRF + SimpleJWT + CORS + LimitOffsetPagination |
| `accounts` app | ✅ `User` (custom), register / login / logout / `users/me` / `users/` |
| `chats` app | ✅ `Chat`, `ChatMember`, `Message`, `ReadReceipt`, `Reaction` + ViewSet'lar |
| `chats/permissions.py` | ✅ `IsChatMember`, `IsMessageOwnerOrAdmin` |
| Channels o'rnatilgan | ✅ `channels 4.3.2` |
| **`chats/consumers.py`** | ✅ `message.create` / `typing` / `read` / `call.signal` |
| **`chats/routing.py`** | ✅ `ws/chat/<chat_id>/`, `ws/global/` |
| **`config/asgi.py` da websocket** | ✅ `ProtocolTypeRouter` |
| **Accounts (multi-login)** | ✅ `/api/accounts/` + `activate` |
| **Folder / Category model** | ✅ `Folder` + `/api/folders/` |
| **Settings / theme saqlash** | ✅ `/api/settings/me/` |
| **Media (attachment) upload** | ✅ `Attachment` + `/api/uploads/` |
| **Bot model** | ❌ yo'q |
| **Channel model** | ❌ (channel = `Chat(is_channel=True)`, maxsus model yo'q) |
| **Calls (WebRTC signaling)** | ✅ `Call` + `/api/calls/` + `call.signal` WS |
| **Wallet** | ❌ yo'q |

**Xulosa:** REST qismi ~70% tayyor. Asosiy ish — **WebSocket** va **multi-account** +
**folder/settings** modellari.

---

## 🎯 1. UMUMIY ARXITEKTURA

```text
messenger.html  (frontend)
   │
   │  fetch()  +  Authorization: Bearer <access>
   ↓
┌──────────────────────────────────────────┐
│  Django + DRF  (REST)                    │
│  /api/auth/  /api/users/  /api/chats/    │
└──────────────────────────────────────────┘
   │
   │  WebSocket  ws://…/ws/?token=<access>
   ↓
┌──────────────────────────────────────────┐
│  Channels  (ASGI)                         │
│  chats/consumers.py                       │
└──────────────────────────────────────────┘
   │                    │
   ↓                    ↓
PostgreSQL           Redis (channel layer)
```

Frontend bitta sahifada barcha ma'lumotni shu tartibda oladi:

```text
1. GET  /api/users/me/            → ME
2. GET  /api/accounts/            → ACCOUNTS[]
3. GET  /api/folders/             → rail (All Chats / Favorite / Bots / …)
4. GET  /api/chats/?folder=all    → CHATS[]
5. GET  /api/chats/{id}/messages/ → chat.messages[]
6. WS   /ws/?token=…              → yangi xabarlar
```

---

## 🧱 2. YANGI MODELLAR

### 2.1 `accounts` — Account (multi-login)

Frontend sidebar'da **Account switcher** bor (Spider-man / Work Account / Freelance).
Bitta brauzerda bir nechata login saqlanishi kerak.

> Muhim: `TokenObtainPairView` **bitta** `access` qaytaradi. Multi-account uchun
> login javobiga `account_id` qo'shiladi, frontend esa `access` token'ni
> `localStorage` da `access:<account_id>` kalit bilan saqlaydi.

```python
# accounts/models.py  — qo'shimchalar

class Account(models.Model):
    """Brauzerdagi bitta login sloti (bir xil User bo'lishi mumkin)."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Faol'
        HIDDEN = 'hidden', 'Yashirilgan'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='accounts'
    )
    label = models.CharField(max_length=60, blank=True)      # "Work Account"
    slot_order = models.PositiveIntegerField(default=0)      # sidebar tartibi
    status = models.CharField(
        max_length=8, choices=Status.choices, default=Status.ACTIVE
    )
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['slot_order', 'id']
        unique_together = ('user', 'label')

    def __str__(self):
        return self.label or self.user.username
```

`User` ga qo'shiladigan maydonlar (frontend'dagi emoji status uchun):

```python
class User(AbstractUser):
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.CharField(max_length=255, blank=True)
    avatar = models.URLField(blank=True)
    emoji_status = models.CharField(max_length=8, default='🕷️')   # YANGI
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
```

### 2.2 `chats` — Folder (sidebar bo'limlari)

```text
☰ Menu
All Chats
PC Favorite
Bots
Football
Python / Linux / HTML
Edit
```

```python
# chats/models.py

class Folder(models.Model):
    class Kind(models.TextChoices):
        SYSTEM = 'system', 'Tizim'      # All Chats, Bots, Edit
        CUSTOM = 'custom', 'Foydalanuvchi'  # PC Favorite, Football, Python…

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='folders'
    )
    slug = models.SlugField(max_length=40)                 # all | favorite | bots | football
    title = models.CharField(max_length=60)                # "PC Favorite"
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.CUSTOM)
    icon = models.CharField(max_length=40, default='i-folder')
    position = models.PositiveIntegerField(default=0)
    accent = models.CharField(max_length=20, blank=True)  # "#8b5cf6"

    class Meta:
        ordering = ['position', 'id']
        unique_together = ('owner', 'slug')

    def __str__(self):
        return f'{self.owner}: {self.title}'
```

`Chat` ga qo'shiladigan maydon:

```python
class Chat(models.Model):
    type = models.CharField(...)          # private | group  (mavjud)
    name = ...
    avatar = ...
    members = ...                          # (mavjud)
    folder = models.ForeignKey(
        Folder, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='chats',
    )                                       # YANGI
    is_channel = models.BooleanField(default=False)   # YANGI
    is_bot = models.BooleanField(default=False)       # YANGI
    is_favorite = models.BooleanField(default=False)  # YANGI
    is_muted = models.BooleanField(default=False)     # YANGI
    is_pinned = models.BooleanField(default=False)    # YANGI
    ...
```

### 2.3 `chats` — Message qo'shimchalari

Frontend'dagi `✓ / ✓✓` (ticks) va `edited` / `deleted` uchun:

```python
class Message(models.Model):
    ...
    is_read = models.BooleanField(default=False)       # mavjud
    is_edited = models.BooleanField(default=False)     # mavjud
    is_deleted = models.BooleanField(default=False)    # mavjud
    attachment = models.ForeignKey(
        'Attachment', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='messages',
    )                                                  # YANGI
    client_id = models.CharField(                      # YANGI — optimistic UI uchun
        max_length=40, blank=True, db_index=True,
        help_text='Frontend yuborgan vaqtincha id (dedup uchun).',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['sender', 'client_id'],
                condition=~models.Q(client_id=''),
                name='unique_sender_client_id',
            ),
        ]


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
    size = models.PositiveBigIntegerField(default=0)   # bytes
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration = models.PositiveIntegerField(null=True, blank=True)  # sekund
    thumbnail = models.ImageField(upload_to='attachments/thumbs/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### 2.4 `users` — Settings (Night Mode, tema)

```python
class UserSettings(models.Model):
    class Theme(models.TextChoices):
        NIGHT = 'night', 'Night'
        DAY = 'day', 'Day'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='settings'
    )
    theme = models.CharField(max_length=5, choices=Theme.choices, default=Theme.NIGHT)
    accent = models.CharField(max_length=20, default='#8b5cf6')
    send_on_enter = models.BooleanField(default=True)
    show_birthday_banner = models.BooleanField(default=True)
    wallpaper = models.URLField(blank=True)   # asosiy chat oynasi foni
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'settings:{self.user_id}'
```

### 2.5 `misc` — Birthday banner va Contacts

```python
class Contact(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name='contacts')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='contact_of')
    nickname = models.CharField(max_length=100, blank=True)
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('owner', 'user')


class Event(models.Model):
    """Tug'ilgan kun banner'i."""

    class Kind(models.TextChoices):
        BIRTHDAY = 'birthday', 'Tug\'ilgan kun'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name='events')
    person_name = models.CharField(max_length=100)
    date = models.DateField()               # MM-DD yil muhim emas
    kind = models.CharField(max_length=9, choices=Kind.choices, default=Kind.BIRTHDAY)
    emoji = models.CharField(max_length=8, default='🎂')
```

### 2.6 `wallet` — Wallet (NEW badge)

```text
╔══════════════════════════════════════════════╗
║  Wallet model                               ║
╠══════════════════════════════════════════════╣
║  currency      USD | UZS | BTC | ETH | TON   ║
║  balance       Decimal                       ║
║  address       CharField (crypto uchun)      ║
║  updated_at    auto_now                      ║
╚══════════════════════════════════════════════╝
```

> MVP da bu faqat **o'qish** (balance ko'rsatish). To'lov yuborish alohida bosqich —
> hozircha stub qiling, keyinroq to'lov provayderi qo'shiladi.

### 2.7 `calls` — Calls

```python
class Call(models.Model):
    class Kind(models.TextChoices):
        VOICE = 'voice', 'Ovozli'
        VIDEO = 'video', 'Video'

    class Status(models.TextChoices):
        MISSED = 'missed', 'Javobsiz'
        OUTGOING = 'outgoing', 'Chiquvchi'
        INCOMING = 'incoming', 'Kiruvchi'
        ENDED = 'ended', 'Tugadi'

    chat = models.ForeignKey('Chat', on_delete=models.CASCADE, related_name='calls')
    initiator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    kind = models.CharField(max_length=5, choices=Kind.choices, default=Kind.VOICE)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.MISSED)
    started_at = models.DateTimeField(null=True, blank=True)
    duration = models.PositiveIntegerField(default=0)   # sekund
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
```

---

## 🔌 3. WEBSOCKET (Channels) — ASOSIY VAZIFA

Bu — eng katta bo'shliq. `channels` o'rnatilgan, lekin **consumer yo'q**.

### 3.1 `config/asgi.py`

```python
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Avval Django ni yuklash SHART (modellar import qilinishi kerak)
django_asgi_app = get_asgi_application()

from chats.routing import websocket_urlpatterns  # noqa: E402  (import pastda!)

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
})
```

> ⚠️ `get_asgi_application()` dan **oldin** `import` yozib bo'lmaydi — aks holda
> `AppRegistryNotReady` xatosi chiqadi.

### 3.2 `chats/routing.py`

```python
from django.urls import path

from chats import consumers

websocket_urlpatterns = [
    path('ws/chat/<int:chat_id>/', consumers.ChatConsumer.as_asgi()),
    path('ws/global/', consumers.GlobalConsumer.as_asgi()),
]
```

### 3.3 `chats/consumers.py`

```python
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer

from chats.models import Chat, ChatMember, Message
from chats.serializers import MessageSerializer


class BaseConsumer(AsyncJsonWebsocketConsumer):
    async def auth(self):
        """?token=<access> orqali autentifikatsiya."""
        from rest_framework_simplejwt.tokens import AccessToken
        from django.contrib.auth import get_user_model

        token = (self.scope.get('query_string') or b'').decode()
        raw = dict(p.split('=', 1) for p in token.split('&') if '=' in p).get('token')
        if not raw:
            return None
        try:
            user = get_user_model().objects.get(pk=AccessToken(raw)['user_id'])
        except Exception:
            return None
        return user

    async def send_error(self, code, detail):
        await self.send_json({'type': 'error', 'code': code, 'detail': detail})


class ChatConsumer(BaseConsumer):
    async def connect(self):
        self.user = await self.auth()
        if not self.user:
            await self.close(code=4401)
            return

        self.chat_id = int(self.scope['url_route']['kwargs']['chat_id'])
        if not await self.is_member(self.chat_id, self.user.pk):
            await self.close(code=4403)
            return

        self.group_name = f'chat_{self.chat_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connected', 'chat_id': self.chat_id})

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        action = content.get('action')

        if action == 'message.create':
            message = await self.create_message(content)
            await self.channel_layer.group_send(
                self.group_name,
                {'type': 'chat.message', 'payload': message},
            )

        elif action == 'typing':
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat.typing',
                    'payload': {'user_id': self.user.pk,
                               'username': self.user.username,
                               'is_typing': bool(content.get('is_typing'))},
                },
            )

        elif action == 'read':
            await self.mark_read(content.get('message_id'))
            await self.channel_layer.group_send(
                self.group_name, {'type': 'chat.read', 'payload': {'user_id': self.user.pk}}
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

    # --- db helpers (sync -> async) ---
    @database_sync_to_async
    def is_member(self, chat_id, user_id):
        return ChatMember.objects.filter(chat_id=chat_id, user_id=user_id).exists()

    @database_sync_to_async
    def create_message(self, content):
        chat = Chat.objects.get(pk=self.chat_id)
        msg = Message.objects.create(
            chat=chat,
            sender=self.user,
            content=(content.get('text') or '').strip(),
            reply_to_id=content.get('reply_to'),
            client_id=content.get('client_id', ''),
        )
        return MessageSerializer(msg).data
```

### 3.4 Frontend WebSocket

`messenger.js` ichidagi `simulateReply()` ni haqiqiy socket bilan almashtiring:

```javascript
const API = 'http://127.0.0.1:8000';
const WS_BASE = 'ws://127.0.0.1:8000';

const store = {
    access: localStorage.getItem('access'),
    refresh: localStorage.getItem('refresh'),
    accountId: localStorage.getItem('account_id'),
};

// 1) Autentifikatsiya + refresh
async function api(path, options = {}) {
    const res = await fetch(API + path, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${store.access}`,
            ...(options.headers || {}),
        },
    });
    if (res.status === 401) {
        await refreshToken();
        return api(path, options);          // bir marta qayta urinish
    }
    return res;
}

async function refreshToken() {
    const res = await fetch(`${API}/api/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: store.refresh }),
    });
    const data = await res.json();
    store.access = data.access;
    localStorage.setItem('access', data.access);
}

// 2) Socket — chat ochilganda ulanadi, yopilganda uziladi
let socket = null;

function openSocket(chatId) {
    closeSocket();
    socket = new WebSocket(`${WS_BASE}/ws/chat/${chatId}/?token=${store.access}`);

    socket.onopen = () => console.log('ws open');
    socket.onclose = (e) => {
        if (e.code === 4401) return logout();
        if (e.code === 4403) return toast('Bu chatga kirish huquqi yo\'q');
        setTimeout(() => openSocket(chatId), 2000);   // reconnect
    };
    socket.onmessage = (e) => handleSocket(JSON.parse(e.data));
}

function closeSocket() {
    if (socket) { socket.onclose = null; socket.close(); socket = null; }
}

function handleSocket({ type, data }) {
    if (type === 'message.new')  return appendMessage(data);
    if (type === 'typing')       return showTyping(data);
    if (type === 'read')         return markTicksRead(data);
    if (type === 'chat.updated') return patchChat(data);
}

// 3) Yuborish — optimistic UI + client_id dedup
async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text) return;

    const clientId = crypto.randomUUID();
    appendMessage({                       // darhol ekranga
        id: null, client_id: clientId, from: 'me', text,
        time: nowClock(), ticks: 'none',
    });

    socket.send(JSON.stringify({ action: 'message.create', text, client_id: clientId }));
}
```

---

## 🌐 4. ENDPOINTLAR TO'LIQ RO'YXATI

### 4.1 Auth (mavjud + kengaytma)

| Method | URL | Body / Query | Izoh |
|---|---|---|---|
| POST | `/api/auth/register/` | `{username,email,password,password_confirm,display_name}` | ✅ mavjud. Javobga `user`, `access`, `refresh` |
| POST | `/api/auth/login/` | `{username, password}` | ✅ mavjud. Username **yoki** email |
| POST | `/api/auth/logout/` | `{refresh}` | ✅ mavjud, refresh blacklist |
| POST | `/api/token/refresh/` | `{refresh}` | ✅ mavjud |
| GET | `/api/users/me/` | — | ✅ mavjud |
| PATCH | `/api/users/me/` | `{display_name,bio,avatar,emoji_status}` | ✅ mavjud + `emoji_status` |
| GET | `/api/users/?search=` | `?search=ali` | ✅ mavjud, chat boshlash uchun |
| **GET** | `/api/users/online/` | — | 🆕 online foydalanuvchilar |
| **PATCH** | `/api/users/me/status/` | `{is_online: true}` | 🆕 presence ping (15s) |

### 4.2 Accounts — switcher 🆕

| Method | URL | Body | Izoh |
|---|---|---|---|
| GET | `/api/accounts/` | — | `[{"id","label","sub","emoji","unread","is_active"}]` |
| POST | `/api/accounts/` | `{label}` | Yangi login slot |
| PATCH | `/api/accounts/{id}/` | `{label, slot_order, status}` | Rename / reorder / hide |
| DELETE | `/api/accounts/{id}/` | — | Slotni o'chirish (User o'chirilmaydi) |
| POST | `/api/accounts/{id}/activate/` | — | `slot_order` ni yuqoriga suradi |

Javob shakli (frontend `ACCOUNTS` ga to'g'ri keladi):

```json
[
  {
    "id": 1,
    "label": "Spider-man",
    "sub": "+998 90 123 45 67",
    "emoji": "🕷️",
    "unread": 3,
    "is_active": true
  },
  { "id": 2, "label": "Work Account", "sub": "w@company.uz",
    "emoji": "💼", "unread": 2165, "is_active": false }
]
```

> `unread` — `accounts.UserSerializer.get_unread_count()` dan olinadi (allaqachon bor).

### 4.3 Folders — sidebar 🆕

| Method | URL | Body | Izoh |
|---|---|---|---|
| GET | `/api/folders/` | — | `[{"id","slug","title","kind","icon","position","accent","chat_count"}]` |
| POST | `/api/folders/` | `{title, icon, accent}` | Yangi papka |
| PATCH | `/api/folders/{id}/` | `{title, icon, position, accent}` | Edit |
| DELETE | `/api/folders/{id}/` | — | O'chirish (chatlar `folder=null`) |
| POST | `/api/folders/reorder/` | `{order: [3, 1, 7]}` | Tartibni saqlash |

Tizim papkalari `GET` da **har doim** birinchi bo'lib keladi va `kind=system`:

```json
[
  {"slug": "all",       "title": "All Chats",           "icon": "i-chats",  "kind": "system", "chat_count": 12},
  {"slug": "favorite",  "title": "PC Favorite",          "icon": "i-star",   "kind": "custom", "chat_count": 3},
  {"slug": "bots",      "title": "Bots",                "icon": "i-bot",    "kind": "system", "chat_count": 1},
  {"slug": "football",  "title": "Football",            "icon": "i-folder", "kind": "custom", "chat_count": 1},
  {"slug": "code",      "title": "Python / Linux / HTML","icon": "i-code",  "kind": "custom", "chat_count": 3},
  {"slug": "edit",      "title": "Edit",                "icon": "i-pencil", "kind": "system", "chat_count": 12}
]
```

### 4.4 Chats — ro'yxat (kengaytirilgan) ✅ + 🆕

| Method | URL | Izoh |
|---|---|---|
| GET | `/api/chats/` | ✅ mavjud. **Qo'shish:** `?folder=slug`, `?search=`, `?unread=true` |
| POST | `/api/chats/` | ✅ mavjud. Body: `{type, name, member_ids, folder, is_channel}` |
| GET | `/api/chats/{id}/` | ✅ mavjud |
| PATCH | `/api/chats/{id}/` | ✅ mavjud. `+ is_favorite, is_muted, is_pinned, folder, name` |
| DELETE | `/api/chats/{id}/` | ✅ mavjud (faqat admin) |
| GET | `/api/chats/{id}/messages/` | ✅ `?limit&offset&before&search&unread` |
| POST | `/api/chats/{id}/messages/` | ✅ `{content, reply_to}` + 🆕 `attachment_id, client_id` |
| GET | `/api/chats/{id}/members/` | ✅ mavjud |
| POST | `/api/chats/{id}/members/` | ✅ `{user_ids: []}` |
| DELETE | `/api/chats/{id}/members/{user_id}/` | ✅ mavjud |
| POST | `/api/chats/{id}/read/` | ✅ mavjud |
| **POST** | `/api/chats/{id}/pin/` | 🆕 `{message_id}` — pinned xabar |
| **POST** | `/api/chats/{id}/typing/` | 🆕 `{is_typing}` (WS bo'lmasa fallback) |

### 4.5 Messages ✅ + 🆕

| Method | URL | Izoh |
|---|---|---|
| GET | `/api/messages/?chat=` | ✅ mavjud |
| GET | `/api/messages/{id}/` | ✅ mavjud |
| PATCH | `/api/messages/{id}/` | ✅ mavjud → `is_edited=True` |
| DELETE | `/api/messages/{id}/` | ✅ soft delete (`is_deleted=True`, `content=''`) |
| POST | `/api/messages/{id}/read/` | ✅ mavjud |
| POST | `/api/messages/{id}/react/` | ✅ `{kind: like\|love\|laugh\|sad}` |
| **POST** | `/api/messages/{id}/forward/` | 🆕 `{to_chat_ids: []}` |

### 4.6 Media 🆕

| Method | URL | Body | Izoh |
|---|---|---|---|
| POST | `/api/uploads/` | `multipart: file` | `{id, kind, url, file_name, size, mime_type, width, height, duration}` |
| GET | `/api/uploads/{id}/` | — | Metadata |
| DELETE | `/api/uploads/{id}/` | — | O'chirish |

Sozlama (`settings.py`):

```python
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024     # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
```

Ruxsat etilgan turlar (whitelist — XSS himoyasi):

```python
ALLOWED_UPLOAD_EXTENSIONS = {
    'image': {'jpg', 'jpeg', 'png', 'gif', 'webp'},
    'video': {'mp4', 'webm', 'mov'},
    'audio': {'mp3', 'ogg', 'm4a', 'wav'},
    'file':  {'pdf', 'docx', 'xlsx', 'zip', 'txt'},
}
```

### 4.7 Contacts, Events, Settings, Wallet, Calls 🆕

| Method | URL | Izoh |
|---|---|---|
| GET | `/api/contacts/` | `[{"id","user":{...},"nickname","is_favorite"}]` |
| POST | `/api/contacts/` | `{user_id, nickname}` |
| PATCH/DELETE | `/api/contacts/{id}/` | — |
| GET | `/api/events/?month=&day=` | Bugungi tug'ilgan kunlar → banner |
| POST | `/api/events/` | `{person_name, date, kind, emoji}` |
| GET | `/api/settings/me/` | `{theme, accent, send_on_enter, show_birthday_banner, wallpaper}` |
| PATCH | `/api/settings/me/` | Yuqoridagilarni yangilash |
| GET | `/api/wallet/` | `{currency, balance, address, updated_at}` |
| GET | `/api/calls/` | `[{"id","chat","kind","status","started_at","duration"}]` |
| POST | `/api/calls/` | `{chat_id, kind}` — chaqiruvni boshlash |
| PATCH | `/api/calls/{id}/` | `{status, duration}` |

---

## 📦 5. FRONTEND ULASH PLANI

### 5.1 Static fayllarni `static/` ga ko'chirish

Hozir `dev_file()` orqali ildiz papkadan beriladi (faqat `DEBUG=True`). Keyin:

```text
messger/
├── static/
│   ├── css/messenger.css
│   ├── js/messenger.js
│   └── img/
├── templates/
│   └── messenger.html
```

`settings.py`:

```python
STATICFILES_DIRS = [BASE_DIR / 'static']
```

`config/urls.py`:

```python
from django.views.generic import TemplateView

urlpatterns += [
    path('messenger/', TemplateView.as_view(template_name='messenger.html'), name='messenger'),
]
```

### 5.2 `messenger.js` ni bosqichma-bosqich real API'ga o'tkazish

| # | Mock (hozir) | Real (keyin) |
|---|---|---|
| 1 | `const ME = {...}` | `await api('/api/users/me/').then(r => r.json())` |
| 2 | `renderAccounts()` | `GET /api/accounts/` |
| 3 | `$$('.rail__item')` (HTML da yozilgan) | `GET /api/folders/` → rail ga render |
| 4 | `CHATS` array | `GET /api/chats/?folder=${state.filter}` |
| 5 | `chat.messages` | `GET /api/chats/${id}/messages/?limit=50` |
| 6 | `localStorage` theme | `GET/PATCH /api/settings/me/` |
| 7 | `setTimeout(simulateReply)` | `WebSocket /ws/chat/${id}/` |
| 8 | `Emoji popover` | `PATCH /api/users/me/` `{emoji_status}` |
| 9 | `banner` → `chatById(2)` | `GET /api/events/?month=8&day=26` |
| 10 | `toast('...')` placeholder | Real endpoint chaqirish + xato ko'rsatish |

### 5.3 CSS tokenlarini backend'dan olish

```python
# settings.py
ACCENT_DEFAULT = '#8b5cf6'
```

```javascript
// app init
document.documentElement.style.setProperty('--accent', userSettings.accent);
```

Theme ham `localStorage` da qolishi mumkin — backend esa **boshqa qurilmada**
bir xil bo'lishi uchun kerak.

---

## 🔒 6. XAVFSIZLIK

* [ ] `?token=` dan **faqat** `access` (qisqa muddatli). `refresh` hech qachon URL da.
* [ ] Consumer'da `self.auth()` `None` qaytarsa `close(code=4401)` — hech qachon
      `accept()` **keyin** emas, balki **oldin** tekshiriladi.
* [ ] `database_sync_to_async` — consumer ichida **hech qachon** sync ORM ishlatilmaydi.
* [ ] `select_related` / `prefetch_related` — `MessageSerializer` har safar
      `read_receipts` va `reactions` ga alohida so'rov yubarmasligi uchun.
* [ ] Rate limit: `django-ratelimit` bilan `message.create` (masalan 20/daqiqa).
* [ ] Upload: faqat `.pdf .jpg …` — mime type ham tekshirilsin, faqat kengaytma emas.
* [ ] `DEBUG=False` da `dev_file()` allaqachon `Http404` beradi ✅ (kod yozilgan).
* [ ] `.env` ga `SECRET_KEY`, `DB_PASSWORD` — hech qachon `git add` qilmaslik.

---

## 🧪 7. TEST REJASI (har bosqichda)

### 7.1 Avval mavjud endpointlarni tekshiring

```powershell
python manage.py test
python manage.py runserver
```

```powershell
# 1) Register
curl.exe -X POST http://127.0.0.1:8000/api/auth/register/ `
  -H "Content-Type: application/json" `
  -d '{"username":"spiderman","email":"spider@mail.uz","password":"Str0ng!Pass","password_confirm":"Str0ng!Pass","display_name":"Spider-man"}'

# 2) Login (username yoki email)
curl.exe -X POST http://127.0.0.1:8000/api/auth/login/ `
  -H "Content-Type: application/json" `
  -d '{"username":"spiderman","password":"Str0ng!Pass"}'

# 3) Token bilan profil
curl.exe http://127.0.0.1:8000/api/users/me/ -H "Authorization: Bearer <ACCESS>"

# 4) Ikkinchi user yarat, chat och
curl.exe -X POST http://127.0.0.1:8000/api/chats/ `
  -H "Authorization: Bearer <ACCESS>" -H "Content-Type: application/json" `
  -d '{"type":"group","name":"Frontend Jamoasi","member_ids":[2]}'

# 5) Xabar yubor
curl.exe -X POST http://127.0.0.1:8000/api/chats/1/messages/ `
  -H "Authorization: Bearer <ACCESS>" -H "Content-Type: application/json" `
  -d '{"content":"Salom!"}'

# 6) WebSocket sinovi
pip install websockets
python -c "import asyncio,websockets;asyncio.run(websockets.connect('ws://127.0.0.1:8000/ws/chat/1/?token=<ACCESS>').__aenter__())"
```

### 7.2 Frontend smoke test

| # | Amal | Kutilgan |
|---|---|---|
| 1 | `/messenger.html` ochilsa | Rail + chat list + "Select a chat…" |
| 2 | ☰ bosilsa | Drawer chapdan ochiladi |
| 3 | Drawer `☰` (collapse) | Panel torayadi, label'lar yashirinadi |
| 4 | Chat tanlansa | Header + xabarlar + composer |
| 5 | Xabar yuborilsa | O'ngda bubble, ✓ belgisi, pastda typing + javob |
| 6 | `Enter` | Yuboradi · `Shift+Enter` — yangi qator |
| 7 | `Ctrl+K` | Search fokusga oladi |
| 8 | Rail bo'limi bosilsa | Faqat o'sha folder chatlari |
| 9 | Search yozilsa | Faqat mos chatlar, `mark` bilan |
| 10 | Xabar ustiga hover | Reply / reaction tugmalari |
| 11 | Night Mode | Och rangli tema, `localStorage` da saqlanadi |
| 12 | Banner ✕ | Yopiladi, saqlanadi |
| 13 | 900px kenglik | Chat list yashirinadi, `←` tugmasi chiqadi |
| 14 | `F12` → Console | **Xato yo'q** |

---

## 📋 8. BOTTOM-UP TODO

### Sprint 1 — WebSocket (eng muhim)
- [ ] `chats/routing.py` yozish
- [ ] `chats/consumers.py` — `ChatConsumer` (message + typing + read)
- [ ] `config/asgi.py` — `ProtocolTypeRouter` bilan almashtirish
- [ ] `redis` o'rnatish + `CHANNEL_LAYERS` (keyin, 1 server uchun InMemory yetarli)
- [ ] `messenger.js` da `simulateReply` → real socket
- [ ] Reconnect + 4401/4403 handling

### Sprint 2 — Accounts
- [ ] `Account` model + migration
- [ ] `LoginSerializer.validate()` ga `account_id` qo'shish
- [ ] `AccountViewSet` (list/create/patch/delete/activate)
- [ ] `User.emoji_status` maydoni
- [ ] Frontend: localStorage `access:<account_id>`, switcher

### Sprint 3 — Folders + Chat flags
- [ ] `Folder` model + `Chat.folder/is_favorite/is_muted/is_pinned/is_channel/is_bot`
- [ ] `FolderViewSet` + reorder action
- [ ] `ChatViewSet` ga `?folder=` filter
- [ ] Frontend: rail dinamik render, Edit rejimi (drag + delete)

### Sprint 4 — Settings / Events
- [ ] `UserSettings` OneToOne + `/api/settings/me/`
- [ ] `Event` model + `/api/events/`
- [ ] Frontend: theme serverdan, banner serverdan

### Sprint 5 — Media
- [ ] `Attachment` model + `/api/uploads/`
- [ ] Pillow o'rnatish, thumbnail
- [ ] Frontend: composer'ga 📎, preview, upload progress

### Sprint 6 — Contacts / Wallet / Calls
- [ ] `Contact` + `/api/contacts/`
- [ ] `Wallet` + `/api/wallet/` (o'qish + balance)
- [ ] `Call` + `/api/calls/`
- [ ] Frontend: menyudagi 3 ta bo'lim real bo'ladi

### Sprint 7 — Hardening
- [ ] Rate limit, upload validation
- [ ] `SELECT_related` optimizatsiyasi (N+1 tekshirish)
- [ ] `pytest` testlar (`tests/test_chats.py`)

---

## 🧩 9. YANGI APP QAYERDA YARATILADI

```powershell
python manage.py startapp settings_app   # yoki nomlash: user_settings
python manage.py startapp contacts
python manage.py startapp uploads
```

`settings.py` ga qo'shish:

```python
INSTALLED_APPS += [
    'user_settings',
    'contacts',
    'uploads',
]
```

Har bir app uchun `urls.py` da `config/urls.py` ga ulanadi:

```python
path('api/', include('user_settings.urls')),
path('api/', include('contacts.urls')),
path('api/', include('uploads.urls')),
```

> `settings` nomi Django moduli bilan to'qnashadi — `user_settings` yoki
> `prefs` nomini ishlatish **majburiy**.

---

## ✅ 10. "Tayyor" deb hisoblash mezoni

- [ ] `GET /api/chats/?folder=code` faqat kod papkasidagi chatlarni qaytaradi
- [ ] Ikki brauzerda bitta chatni ochsa, xabar **bir zumda** ikkalasida ko'rinadi
- [ ] Token yo'q WebSocket darhol `4401` bilan yopiladi
- [ ] Ikki account `localStorage` da aralashib ketmaydi
- [ ] Theme sahifani reload qilsa ham saqlanadi
- [ ] Mobil kenglikda chat list / chat area navbatma-navbat ko'rinadi
- [ ] `python manage.py test` yashil
- [ ] Frontend konsolida birorta ham xato yo'q
