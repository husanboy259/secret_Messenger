Frontend roadmaplari bilan parallel olib boriladigan **Backend roadmap**. Stack: `Django → Django REST Framework → SimpleJWT → PostgreSQL → Redis → Channels (WebSocket)`. Hozirgi holat: Django 6.1.1 + Python 3.13 o'rnatilgan, loyiha va `accounts` app yaratilgan, SQLite ishlayapti (keyin PostgreSQL'ga o'tasiz).

# 🟢 BACKEND ROADMAP — MESSGER

## 0-BOSQICH — Tayyorlash (Siz shu yerda turibsiz)

Loyiha strukturasi:

```text
messger/
│
├── config/          # Asosiy sozlamalar (settings.py, urls.py)
├── accounts/        # Foydalanuvchi ilovasi (siz yaratyapsiz)
├── index.html       # Frontend
├── login.html       # Frontend
└── manage.py
```

Kerakli bilimlar (boshlashdan oldin):

* [ ] Python asoslari (funksiyalar, klasslar, modullar)
* [ ] Pip (paket o'rnatish)
* [ ] Virtual environment (venv)
* [ ] HTTP asoslari: GET, POST, PUT, DELETE
* [ ] JSON nima

Paketlar:

```text
django                     # Web framework
djangorestframework        # REST API
djangorestframework-simplejwt  # JWT autentifikatsiya
django-cors-headers        # CORS (frontend bilan ulash)
psycopg2                   # PostgreSQL haydovchisi (keyin kerak)
channels                   # WebSocket (keyin keyin)
daphne                     # Channels ASGI serverni ishga tushirish
redis                      # Redis cache/channel layer (keyin)
```

> 🎯 Eslatma: Agar `config/settings.py` da `corsheaders` xatolik bersa, avval `pip install django-cors-headers` qiling.

---

## 🟢 1-BOSQICH — Django asoslari (1-oy)

### O'rgan:

* [ ] Django loyihasi nima, app nima
* [ ] `manage.py` buyruqlari: `runserver`, `startapp`, `migrate`, `makemigrations`, `createsuperuser`, `shell`
* [ ] `models.py` — ma'lumotlar bazasi modellari
* [ ] `views.py` — HTTP javoblarni qaytarish
* [ ] `urls.py` — URL yo'naltirish
* [ ] Admin panel (`admin.py`)

### Mini-projectlar:

```text
1. Hello World view
2. Oddiy blog modeli (Post, Comment)
3. Ma'lumotlar bazasiga CRUD
```

### Amaliyot:

```bash
python manage.py runserver        # serverni ishga tushirish
python manage.py makemigrations   # migratsiya yaratish
python manage.py migrate          # bazaga qo'llash
python manage.py createsuperuser # admin yaratish
```

---

## 🟢 2-BOSQICH — PostgreSQL (1-2-oy)

SQLite o'rganishdan keyin PostgreSQL'ga o'ting.

### O'rgan:

* [ ] PostgreSQL o'rnatish va ishga tushirish
* [ ] `createdb`, `psql` buyruqlari
* [ ] Jadval (table) yaratish
* [ ] Primary key, foreign key
* [ ] JOIN
* [ ] Bitta rasmli: users, chats, messages

### Django'da ulash (`settings.py`):

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'messger',
        'USER': 'messger',
        'PASSWORD': 'parolingiz',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}
```

> Sizning `settings.py` allaqachon env orqali `DB_ENGINE=postgresql` desangiz PostgreSQL'ga o'tadigan qilib tayyorlangan.

---

## 🟢 3-BOSQICH — Foydalanuvchi (Auth) (2-oy)

Bu — **backendning birinchi haqiqiy qismi**. 0-bosqichda `accounts` app va custom User model uchun `AUTH_USER_MODEL = 'accounts.User'` sozlangan.

### Custom User model (`accounts/models.py`):

```python
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.CharField(max_length=255, blank=True)
    avatar = models.URLField(blank=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
```

### Auth endpointlari:

* [ ] Ro'yxatdan o'tish (Register)
* [ ] Kirish (Login) → JWT token olish
* [ ] Refresh token
* [ ] Profilni ko'rish / yangilash
* [ ] Logout (token blacklist)

### Endpointlar ro'yxati:

```text
POST /api/auth/register/     # Ro'yxatdan o'tish
POST /api/token/             # Kirish → access + refresh token
POST /api/token/refresh/     # Yangi access token
GET  /api/users/me/          # Profilim
PATCH /api/users/me/         # Profilni yangilash
```

---

## 🔵 4-BOSQICH — Django REST Framework (3-oy)

### O'rgan:

* [ ] DRF nima, nima uchun kerak
* [ ] `serializers.py` — ma'lumotlarni JSON'ga aylantirish
* [ ] `views.py` — APIView, ViewSet
* [ ] `@api_view`, `GenericViewSet`
* [ ] Django REST Framework validation
* [ ] DRF settings (`REST_FRAMEWORK` sozlamasi)

### Serializer misoli:

```python
from rest_framework import serializers
from accounts.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'display_name', 'avatar']
```

### Amaliyot:

* [ ] Register serializer + view
* [ ] Login serializer
* [ ] Token olish
* [ ] `/api/users/me/` endpoint

> Sizning `config/settings.py` da DRF allaqachon sozlangan (JWT + permissions).

---

## 🔵 5-BOSQICH — JWT Autentifikatsiya (4-oy)

### O'rgan:

* [ ] Token nima, JWT (JSON Web Token) nima
* [ ] Access token vs Refresh token
* [ ] `Authorization: Bearer <token>` header
* [ ] SimpleJWT ishlatish
* [ ] Token muddati (lifetime) sozlash
* [ ] Login: username-ga ko'ra emas, username YOKI email orqali kirish

### Kiritish (allaqachon tayyor):

`config/settings.py`:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

### `config/urls.py`:

```python
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
]
```

---

## 🟢 6-BOSQICH — Frontend bilan ulash (4-oy)

### CORS

Frontend boshqa portda (masalan `5500`) ishlasa, CORS kerak.

* [ ] `django-cors-headers` o'rnatish
* [ ] `CORS_ALLOWED_ORIGINS` sozlash (sizning settings allaqachon tayyor)

### `login.html` da:

```javascript
fetch('http://127.0.0.1:8000/api/token/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
})
.then(r => r.json())
.then(data => {
    localStorage.setItem('access', data.access);
    localStorage.setItem('refresh', data.refresh);
});
```

* [ ] Login formani backendga ulash
* [ ] Register formani yaratish
* [ ] Access token'ni localStorage'ga saqlash
* [ ] `Authorization: Bearer <token>` bilan /me/ chaqirish
* [ ] 401 bo'lsa → refresh token bilan yangilash

---

## 🟣 7-BOSQICH — Chat va Xabarlar (Messenger core) (5-oy)

### Modellar:

`chats` app yaratasiz:

```text
Chat          # Suhbat (1-to-1 yoki guruh)
├── id
├── type         (private | group)
├── members      (ManyToMany → User)
├── name         (guruh uchun)
└── avatar       (guruh uchun)

Message       # Xabar
├── id
├── chat         (ForeignKey → Chat)
├── sender       (ForeignKey → User)
├── content      (Text)
├── created_at   (DateTime)
├── is_read      (Boolean)
├── edited       (Boolean)
└── reply_to     (ForeignKey → Message)

ReadReceipt  # O'qildi belgisi
├── message      (ForeignKey → Message)
├── user         (ForeignKey → User)
└── read_at
```

### Endpointlar:

```text
GET    /api/chats/                  # Men qatnashgan chatlar
POST   /api/chats/                  # Yangi chat (private → member_id + / group)
GET    /api/chats/{id}/             # Bitta chat
GET    /api/chats/{id}/messages/    # Chat xabarlari (pagination/offset)
POST   /api/chats/{id}/messages/    # Xabar yuborish
PATCH  /api/messages/{id}/          # Xabarni tahrirlash
DELETE /api/messages/{id}/          # Xabarni o'chirish
POST   /api/messages/{id}/read/     # O'qildi deb belgilash
```

### Amaliyot:

* [ ] `chats` app yaratish
* [ ] Modellarni yozish
* [ ] Serializerlar
* [ ] ViewSet'lar
* [ ] Permission: faqat chat a'zolari xabarni ko'ra oladi
* [ ] Pagination (100 ta xabardan keyin load more)

---

## 🔴 8-BOSQICH — WebSocket / Realtime (6-oy)

HTTP bilan chat qila olmaysiz — WebSocket kerak.

### O'rgan:

* [ ] WebSocket nima, HTTPdan farqi
* [ ] `channels` paketi
* [ ] ASGI (`asgi.py`)
* [ ] Consumer'lar (sync / async)
* [ ] Routing (`channels.routing`)

### O'rnatish:

```text
pip install channels daphne
```

### Consumer misoli:

```python
# chats/consumers.py
import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer

class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['chat_id']
        self.group_name = f'chat_{self.room_name}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def receive_json(self, content):
        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'chat.message', 'message': content}
        )

    async def chat_message(self, event):
        await self.send_json(event['message'])
```

### Frontend WebSocket:

```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/ws/chat/1/?token=' + access);
ws.onmessage = (e) => { /* xabarni ekranga chiqarish */ };
ws.send(JSON.stringify({ message: 'Salom' }));
```

* [ ] Xabar yuborish → hobby davomida darhol chiqadi
* [ ] `broadcast` — barcha a'zolarga yetib boradi
* [ ] Reconnect (uzilsa qayta ulanish)
* [ ] JWT token orqali WebSocket autentifikatsiya

---

## 🟡 9-BOSQICH — Redis (7-oy)

WebSocket ko'plab serverlar bilan ishlaganda xabarlar "channel layerga" kerak bo'ladi.

### O'rgan:

* [+] Redis nima (in-memory data store)
* [+] Cache
* [+] Channel layer (WebSocket)

### Sozlash:

```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [('127.0.0.1', 6379)]},
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

* [ ] Redis o'rnatish (Windowsda Memurai / WSL)
* [ ] Chat xabarlarini cache'da saqlash
* [ ] Online/offline statusni Redis'da saqlash

---

## 🟡 10-BOSQICH — Chat qo'shimcha funksiyalar (8-oy)

* [ ] Typing indicator (yozmoqda...)
* [ ] Online/offline status (`last_seen`)
* [ ] O'qilganlik (read receipts: ✓ ✓)
* [ ] Xabarni o'chirish (delete for me / for everyone)
* [ ] Reply, forward
* [ ] Reaction (emoji)
* [ ] Media yuklash (rasm, video, fayl)
* [ ] Qidiruv (xabar va foydalanuvchi)
* [ ] Guruh yaratish va a'zo qo'shish
* [ ] Admin (guruh egasi, moderator)    
* [ ] Bloklash (block/unblock)
* [ ] Arxivlash, pin

---

## 🔵 11-BOSQICH — Xavfsizlik (9-oy)

* [ ] Password hashing (`make_password` / DRF validation)
* [ ] `django.contrib.auth.password_validation`
* [ ] Rate limiting (ko'p so'rovlarni cheklash — `django-ratelimit`)
* [ ] Token blacklist (logout)
* [ ] CORS (chet el originlardan himoya)
* [ ] File upload validation (hajm, tur)
* [ ] SQL injection, XSS, CSRF haqida tushuncha
* [ ] `.env` — maxfiy kalitlarni saqlash (SECRET_KEY, DB_PASSWORD)

---

## 🟣 12-BOSQICH — Produksiya (10-oy)

### Deploy:

```text
Django
 └── gunicorn / daphne   (web server)
      └── Nginx          (reverse proxy + static)
           └── Domain    (messger.example.com)
```

* [ ] `DEBUG = False`
* [ ] `ALLOWED_HOSTS` to'g'irlash
* [ ] Static/Media fayllar (WhiteNoise / S3)
* [ ] HTTPS (Let's Encrypt)
* [ ] PostgreSQL produksiyada
* [ ] Redis produksiyada
* [ ] Logging (xatolarni kuzatish)
* [ ] Backup (ma'lumotlar zaxirasi)
* [ ] Testlar (`pytest` / Django TestCase)

---

# 🏆 Oxirgi Backend Stack

```text
Python
  ↓
Django
  ↓
Django REST Framework
  ↓
PostgreSQL
  ↓
Redis
  ↓
Channels (WebSocket)
  ↓
JWT (SimpleJWT)
  ↓
Docker / Deploy
```

Loyiha tuzilishi (yakuniy):

```text
config/
│   settings.py
│   urls.py
│   asgi.py
│
accounts/
│   models.py         # User
│   serializers.py
│   views.py
│   urls.py
│
chats/
│   models.py         # Chat, Message
│   serializers.py
│   views.py
│   urls.py
│   routing.py
│   consumers.py
```

---

# 🎯 Sizga to'g'ri tartib (endi darhol boshlang)

```text
1. Django asoslari            → 1-oy
2. SQLite'da auth narsasi      → 2-oy
3. DRF billen API             → 3-oy
4. JWT + login.html ulash      → 4-oy
5. Chat modellar + REST        → 5-oy
6. WebSocket (Channels)        → 6-oy
7. Redis, media, xavfsizlik    → 7-9-oy
8. Deploy                      → 10-oy
```

> 💡 Eng muhimi: har bosqichda **tekshirib ko'ring** — har endpointni `http://127.0.0.1:8000/` dan sinab ko'ring (yoki Postman) va xatoni o'zingiz tuzating. Shu yo'l bilan o'rganish tezlashadi.

Sizning frontend (React + TypeScript + WebSocket) va backend (Django + PostgreSQL + Redis) birlashganda — haqiqiy Messger MVP tayyor bo'ladi. 🚀