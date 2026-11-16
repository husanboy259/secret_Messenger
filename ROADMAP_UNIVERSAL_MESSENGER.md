# Universal Messenger — To'liq Roadmap

> Maqsad: mavjud `messger` loyihasini Telegram darajasidagi messenjer va Premium ekotizimga aylantirish.  
> Holat: `accounts/`, `chats/`, `frontend/`, WebSocket chat/ovozli xabar/qo'ng'iroq asoslari mavjud. Ushbu hujjat mavjud kod ustiga bosqichma-bosqich kengaytirish rejasidir.

## 0. Hozirgi holat (baseline)

- **Stack:** Django 6.1 + DRF + SimpleJWT + Channels, frontend (vanilla HTML/CSS/JS), PostgreSQL/SQLite, Vercel+Render deploy.
- **Mavjud:** auth (register/login/logout, username/email), profil (`/users/me`), ommaviy profil `/open/<username>`, shaxsiy chat, guruh/kanal, papkalar, xabarlar (reply/edit/delete/reaction/read), attachment/ovozli xabar, WebRTC audio/video call signali, real-time WS (`chat_<id>`, `user_<id>`), AI support bot hook (`chats/bot.py`), i18n (uz/ru/en).
- **Keyingi ish:** barqarorlik, xavfsizlik, premium/monetizatsiya va kengaytirilgan messenger funksiyalari.

---

## 1. Universal Messenger — Core

### 1.1 Account va profil
- [x] Ro'yxatdan o'tish va login (username/email)
- [x] Username, display name, bio, avatar, emoji status
- [x] Online/last seen (asosiy)
- [x] Profilni tahrirlash, ommaviy profil va ulashish linki
- [ ] Telefon raqami orqali tasdiqlash (OTP/SMS provider)
- [ ] Video avatar
- [ ] Privacy sozlamalari (last seen, avatar, forward, calls)
- [ ] Block / Unblock / Report
- [ ] Bir nechta akkaunt (multi-account UX + sessionlar)
- [ ] QR orqali profil ulashish
- [ ] Login session va qurilmalarni boshqarish
- [ ] Two-Factor Authentication (2FA/TOTP)
- [ ] Account recovery

### 1.2 Shaxsiy chat
- [x] Real-time WebSocket messaging
- [x] Text, photo/video/audio/voice, document (asosiy attachment)
- [x] Reply, forward (asosiy), edit, delete for me/everyone
- [x] Reactions, pin, typing, read receipts, unread counter
- [x] Chat search, history, draft/optimistik yuborish (qisman)
- [ ] Mentions, hashtaglar, message scheduling, silent messages
- [ ] Sent/Delivered holatlari (alohida)
- [ ] Auto-delete, one-time view media
- [ ] Shared media gallery, chat wallpaper (per-chat)
- [ ] Voice-to-text, message translation

### 1.3 Guruhlar
- [x] Guruh yaratish, avatar, about/bio, invite link, public/private, username
- [x] A'zolar boshqaruvi, admin rollari (asosiy), join flow
- [ ] Custom admin permissions, join requests oqimi (to'liq), qoidalar
- [ ] Topics (forum), slow mode, anti-spam, recent actions
- [ ] Guruh voice/video chat (multi-party), welcome messages, botlar
- [ ] Guruh analitika va boost

### 1.4 Kanallar
- [x] Kanal yaratish, public/private, username, invite, post yozish (asosiy)
- [ ] Cheksiz auditoriya uchun optimizatsiya (fan-out/cursor pagination)
- [ ] Polls, album post, comments/discussion group, scheduled posts
- [ ] Post views/forward stats, statistika, paid content/subscriptions
- [ ] Kanal stories/boosts

### 1.5 Stories
- [ ] 24 soatlik stories (photo/video/text), viewers, reactions/replies
- [ ] Privacy, close friends, archive/highlights/albums, repost/mentions/stickers/links

### 1.6 Qo'ng'iroqlar
- [x] 1:1 audio/video (WebRTC + WS signaling, kiruvchi chaqirish UI, qabul/rad)
- [x] Call history/log (asosiy), mute/camera switch (qisman)
- [ ] Group audio/video, screen sharing, call links
- [ ] Call quality indicator, background noise reduction
- [ ] E2EE dizayni (alohida protokol, cloud chatdan ajratilgan)

### 1.7 Qo'shimcha
- [x] Saved Messages (tekshirish/kengaytirish), chat folders, archive/pin, global search (asosiy)
- [x] Stickers/GIF/emoji (asosiy UI joylari), notifications, dark/light, til tanlash
- [ ] Contacts sync, location/live location, polls/quizzes
- [ ] Bots API, inline bots, Mini Apps, payments (platformaga mos)
- [ ] Multi-device sync, desktop notifications, mavzular to'plami

---

## 2. Universal Premium

### 2.1 Premium profil
- [ ] Premium badge, animated avatar, maxsus rang/uslub, emoji status
- [ ] Profil fonlari/effektlari, maxsus app icon

### 2.2 Premium chat
- [ ] Message effects, premium reactions/stickers/emoji packs
- [ ] Chat ranglari/wallpaper, advanced folders, saved tags
- [ ] Voice-to-text, video transcription, real-time translation, advanced scheduling

### 2.3 Limitlar (taklif, dastlabki)

| Funksiya | Free | Premium |
|---|---:|---:|
| File upload | 100 MB | 2 GB |
| Chat folders | 5 | 20 |
| Pinned chats | 5 | 20 |
| Custom themes | 3 | Unlimited |
| Premium stickers | Yo'q | Ha |
| Voice transcription | Cheklangan | Kengaytirilgan |
| Animated avatar | Yo'q | Ha |
| Profile badge | Yo'q | Ha |
| Custom reactions | Asosiy | Kengaytirilgan |
| Translation | Asosiy | Kengaytirilgan |

### 2.4 Premium AI
- [ ] AI assistant, professional rewrite, grammar, translation, summarization
- [ ] AI transcription, smart replies, chat history summary, sticker generator

### 2.5 Premium media
- [ ] Katta fayl, tez yuklab olish, cloud media management
- [ ] Original/HD media, kengaytirilgan storage, albums, premium kutubxona

---

## 3. Obuna va to'lov (taklif)
- **Paketlar:** Free / Monthly / Yearly (Lifetime hozircha yo'q).
- **Funksiyalar:** checkout, auto-renew, cancel/restore, history, expiration, invoices, promo/referral, gift, admin grant, refund.
- **Qoida:** Premium holati faqat frontendda emas — server to'lovni tasdiqlaydi va entitlement/muddati nazorat qiladi. Rasmiy payment provider va platforma qoidalariga amal qilinsin.

**Backend obyektlari (reja):** `Subscription`, `PremiumPlan`, `Payment`, `PaymentEvent`, `PremiumFeature`, `UserEntitlement`.  
**Arxitektura:** `if user.is_premium` tarqoqligini kamaytirish uchun markaziy **entitlement service**.

---

## 4. Arxitektura yo'nalishi
- **Frontend:** hozirgi web + React/TypeScript migratsiya (bosqichma), keyin Flutter mobile.
- **Backend:** Django + DRF, Channels (WS), Celery (background), Redis (cache/layer), PostgreSQL, S3-compatible storage.
- **Qo'ng'iroq:** WebRTC (TURN/STUN prod), signal WS orqali.
- **Struktura (maqsad):** `apps/` ichida `accounts, messaging, groups, channels, stories, calls, media, payments, subscriptions, premium, ai_assistant, moderation` va `services/`, `websocket/`.

---

## 5. 12 bosqichli ijro rejasi (qisqa)
1. **Foundation:** auth/profile mustahkamlash, API/WS arxitektura, migratsiyalar tartibi.
2. **Messaging Engine:** statuslar, forwarding/scheduling, ishonchli delivery.
3. **Media System:** upload pipeline, compression, storage, voice/video metadata.
4. **Groups & Channels:** permissions, topics, channel features, stats.
5. **Stories & Social:** stories, privacy, saved/social elementlar.
6. **Calls:** barqaror 1:1, keyin group/screen share/call links.
7. **Security:** 2FA, sessions, rate limit, spam/moderation, audit, privacy.
8. **Premium Engine:** plans, subscription, payment verify, entitlements, expiration jobs.
9. **Premium Features:** badge/themes/limits/transcription/translation.
10. **Bots & Mini Apps:** bot API, permissions, SDK/integrations.
11. **AI Ecosystem:** assistant, summaries, smart replies, translation.
12. **Production Launch:** load/security test, monitoring, backup, mobile/desktop.

---

## 6. Xavfsizlik
- HTTPS/WSS, kuchli parol hashing (Argon2), JWT rotation/blacklist, 2FA, session nazorati.
- Rate limiting, brute-force/spam himoyasi, fayl turi/hajmi validatsiyasi, xavfsiz media access.
- Audit log, backup/restore, privacy va account deletion oqimi.
- E2EE faqat alohida, tekshirilgan protokol bilan; oddiy cloud va E2EE chatlarni ajratish.

## 7. Original yo'nalishlar
- **Universal AI:** chat ichida yordamchi, tarjima, qisqartirish.
- **Activity Status:** foydalanuvchi faoliyati (ixtiyoriy/privacy bilan).
- **Universal Cloud:** shaxsiy fayl/media drive.
- **Profile Studio:** rang/animatsiya/banner dizayn.

## 8. Release kesmalari
- **v1.0:** private/group chat, calls, media, profiles, notifications, search, security basics.
- **v2.0:** channels, stories, stickers, bots, mini apps, saved messages.
- **v3.0:** subscription engine + premium features/limits + AI.
- **v4.0:** mobile/desktop, scaling, analytics, bot ecosystem.

## 9. Haftalik development rejasi (boshlang'ich, moslashuvchan)

| Hafta | Fokus | Asosiy vazifalar | Natija / tekshiruv |
|---|---|---|---|
| 1 | Stabilizatsiya | Bugfix, chat ochilish/WS/call barqarorligi, perf (prefetch, render), loglarni tozalash | `manage.py check`, JS syntax, asosiy oqimlar ishlaydi |
| 2 | Auth & profil | Session/device ro'yxati (asosiy), privacy maydonlari, block/report model+API skeleti | Migratsiya + endpointlar + UI stub |
| 3 | Messaging UX | Sent/delivered holati, mention/hashtag parsing (UI), chat search yaxshilash | Xabar holatlari ko'rinadi, qidiruv aniqroq |
| 4 | Guruh/kanal | Admin permission matritsasi, join request oqimi, invite/link boshqaruvi | Rollar cheklovi serverda enforced |
| 5 | Media | Upload limit/validatsiya, media gallery endpoint, thumbnail/metadata | Katta fayl va xavfsiz media flow |
| 6 | Qo'ng'iroq | 1:1 call sifatini yaxshilash, call history UI, reconnect handling | Call log to'liq, uzilishlar kamroq |
| 7 | Xavfsizlik | 2FA (TOTP) dizayn+boshlanish, rate limit, audit log asoslari | Himoya qatlamlari yoqiladi |
| 8 | Premium engine | Plan/Subscription/Payment/Entitlement modellari, entitlement service | Obuna holati serverda hisoblanadi |
| 9 | Premium features | Badge/limitlar/tema cheklovlari, feature gating | Free vs Premium farqi ishlaydi |
| 10 | AI & bot | Bot javob tezligi/streaming, context va handoff, AI assist stub | Support bot barqaror va tezroq |
| 11 | Stories/Channels+ | Stories MVP yoki channel stats/polls (birini tanlash), optimizatsiya | Yangi modul MVP |
| 12 | Release tayyorgarlik | Test, monitoring, backup, deploy hardening, hujjatlarni yangilash | v1/v1.x release checklist yopiladi |

> Har hafta oxiri: demo, regression tekshiruv, roadmap checkbox yangilash, keyingi hafta prioritetini qayta baholash.

---
*Ushbu hujjat `ROADMAP_BACKEND.md`, `ROADMAP_FRONTEND.md`, `ROADMAP_AI_BOT.md` bilan birga yuritiladi; bajarilgan bandlar `[x]` qilib yangilanadi.*
