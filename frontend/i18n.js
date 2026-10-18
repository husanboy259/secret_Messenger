/* Messger i18n — uz / ru / en.
 *
 * Ishlatish:
 *   <script src="i18n.js"></script>
 *   MESSGER_I18N.t('open.message')
 *   MESSGER_I18N.setLang('ru')
 *   <span data-i18n="open.join"></span>
 *   <span data-i18n-html="login.hero_title"></span>   // <br> kabi teglar bilan
 *   <input data-i18n-placeholder="login.username">
 *   <div class="lang-switch"></div>                    // avtomatik tugmalar
 *   <select data-lang-select>...</select>              // avtomatik bog'lanadi
 *
 * Til localStorage'da 'lang' kalitida saqlanadi va settings orqali
 * backend'ga ham yoziladi (UserSettings.language).
 */
(function () {
    'use strict';

    var DICT = {
        uz: {
            'common.brand': "Messger",
            'common.loading': "Yuklanmoqda…",
            'common.retry': "Qayta urinish",
            'common.copy': "Nusxalash",
            'common.copied': "Nusxalandi",
            'common.cancel': "Bekor qilish",
            'common.save': "Saqlash",
            'common.close': "Yopish",
            'common.language': "Til",
            'common.error': "Xatolik yuz berdi",

            'nav.home': "Bosh sahifa",
            'nav.profile': "Profil",
            'nav.login': "Kirish",
            'nav.messages': "Xabarlar",

            'open.profile': "Profil",
            'open.user': "Foydalanuvchi",
            'open.group': "Guruh",
            'open.channel': "Kanal",
            'open.online': "online",
            'open.members': "{n} a'zo",
            'open.message': "Xabar yozish",
            'open.join': "Qo'shilish",
            'open.joined': "A'zosiz",
            'open.open_chat': "Chatni ochish",
            'open.copy_link': "Havolani nusxalash",
            'open.open_in_app': "Messger'da ochish",
            'open.not_found': "Profil topilmadi",
            'open.not_found_desc': "Bu havola o'chirilgan yoki noto'g'ri kiritilgan.",
            'open.loading_profile': "Profil yuklanmoqda…",
            'open.back': "Bosh sahifa",
            'open.about': "Ma'lumot",
            'open.link_copied': "Havola nusxalandi",

            'settings.title': "Sozlamalar",
            'settings.night_mode': "Tungi rejim",
            'settings.language': "Til",
            'settings.my_profile': "Mening profilim",
            'settings.new_folder': "Yangi papka",
            'settings.new_group': "Yangi guruh",
            'settings.new_channel': "Yangi kanal",
            'settings.contacts': "Kontaktlar",

            'app.search': "Qidirish",
            'app.message': "Xabar...",
            'app.manage': "Boshqarish",
            'app.members_title': "A'zolar va adminlar",
            'app.new_chat': "Yangi chat",

            'auth.back_home': "Bosh sahifaga qaytish",

            'login.doc_title': "Kirish — Messger",
            'login.hero_title': "Do'stlaringiz bilan<br>yana bog'laning",
            'login.hero_desc': "Tezkor, xavfsiz va real-time xabarlar. Qaysi qurilmada bo'lishingizdan qat'i nazar — do'stlaringiz har doim yaqin.",
            'login.mock1': "Salom! Tanishganimdan xursandman 🎉",
            'login.mock2': "Men ham! Real-time xabarlar ishlamoqda ⚡",
            'login.brand_online': "Onlayn",
            'login.brand_free': "Bepul",
            'login.brand_safe': "Xavfsiz",
            'login.welcome': "Xush kelibsiz!",
            'login.subtitle': "Messger hisobingizga kiring",
            'login.username': "Foydalanuvchi nomi yoki Email",
            'login.username_ph': "Masalan: sardor_dev",
            'login.password': "Parol",
            'login.remember': "Meni eslab qol",
            'login.forgot': "Parolni unutdingizmi?",
            'login.submit': "Kirish",
            'login.no_account': "Hisobingiz yo'qmi?",
            'login.register': "Ro'yxatdan o'tish",
            'login.registered_ok': "Muvaffaqiyatli ro'yxatdan o'tdingiz! Endi kiring. 🎉",
            'login.err_fill': "Username va parolni to'ldiring.",
            'login.err_server': "Serverga ulanib bo'lmadi. Django ishlayotganini tekshiring.",

            'reg.doc_title': "Ro'yxatdan o'tish — Messger",
            'reg.title': "Ro'yxatdan o'tish",
            'reg.subtitle': "Messger hisobingizga kiring",
            'reg.password_hint': "kamida 8 belgi",
            'reg.hero_title': "Hisob yarating<br>suhbatni boshlang",
            'reg.hero_desc': "Bir daqiqada ro'yxatdan o'ting va do'stlaringiz bilan real-time muloqotni boshlang.",
            'reg.mock1': "Yangi xabaringiz bor 📩",
            'reg.mock2': "Ro'yxatdan o'tish 1 daqiqa davom etadi ✨",
            'reg.username': "Foydalanuvchi nomi",
            'reg.username_ph': "sardor_dev",
            'reg.email': "Email",
            'reg.optional': "ixtiyoriy",
            'reg.email_ph': "email@example.com",
            'reg.password': "Parol",
            'reg.password_ph': "••••••••",
            'reg.password2': "Parolni takrorlang",
            'reg.submit': "Ro'yxatdan o'tish",
            'reg.have_account': "Hisobingiz bormi?",
            'reg.login': "Kirish",
            'reg.err_match': "Parollar mos kelmadi.",
            'reg.err_short': "Parol kamida 8 belgidan iborat bo'lishi kerak.",
            'reg.err_default': "Ro'yxatdan o'tish muvaffaqiyatsiz.",
            'reg.pw_strength': "Parol kuchi: ",
            'reg.pw0': "Juda zaif",
            'reg.pw1': "Zaif",
            'reg.pw2': "O'rtacha",
            'reg.pw3': "Yaxshi",
            'reg.pw4': "Kuchli",

            'join.doc_title': "Guruhga qo'shilish — Messger",
            'join.channel_fallback': "Kanal",
            'join.group_fallback': "Guruh",
            'join.meta': "{n} a'zo · {type}",
            'join.open_group': "Guruhni ochish",
            'join.join': "Qo'shilish",
            'join.request': "So'rov yuborish",
            'join.joined_ok': "Qo'shildingiz ✓",
            'join.sending': "Yuborilmoqda…",
            'join.request_sent': "So'rov yuborilgan",
            'join.request_rejected': "So'rov rad etilgan",
            'join.wait_admin': "Admin tasdiqlashini kuting.",
            'join.private_note': "Xususiy guruh — admin tasdiqlagach qo'shilasiz.",
            'join.login_join': "Kirish va qo'shilish",
            'join.login_needed': "Guruhga qo'shilish uchun tizimga kiring.",
            'join.bad_link': "Havola noto'g'ri",
            'join.bad_link_desc': "Guruh havolasi (code) topilmadi.",
            'join.not_found': "Topilmadi",
            'join.not_found_desc': "Bunday guruh mavjud emas yoki havola eskirgan.",
            'join.err_join': "Qo'shib bo'lmadi.",
            'join.err_server': "Serverga ulanib bo'lmadi.",

            'profile.doc_title': "Profil — Messger",
            'profile.fallback_name': "Foydalanuvchi",
            'profile.fallback_username': "foydalanuvchi",
            'profile.fallback_bio': "Salom! Men Messger'da sizga xabar yozaman. 🚀",
            'profile.edit': "Profilni tahrirlash",
            'profile.to_messages': "Xabarlarga o'tish",
            'profile.copy_link': "Havolani nusxalash",
            'profile.link_copied': "Profil havolasi nusxalandi",
            'profile.copy_hint': "Profil havolasini nusxalash",
            'profile.email': "Email",
            'profile.last_seen': "So'nggi ko'rilgan",
            'profile.chats': "Chatlar",
            'profile.chats_n': "{n} ta suhbat",
            'profile.chats_zero': "0 ta suhbat",
            'profile.side_title': "Profil malumotlari",
            'profile.side_name': "Ism",
            'profile.side_username': "Foydalanuvchi nomi",
            'profile.side_status': "Holat",
            'profile.online': "Online",
            'profile.account': "Hisob",
            'profile.logout': "Chiqish",
            'profile.edit_title': "Profilni tahrirlash",
            'profile.label_name': "Ism",
            'profile.label_bio': "Bio",
            'profile.label_avatar': "Avatar",
            'profile.avatar_ph': "https://... rasm manzili",
            'profile.err_name': "Ism bo'sh bo'lishi mumkin emas.",
            'profile.saving': "Saqlanmoqda...",
            'profile.saved_local': "Serverda saqlanmadi. Local saqlandi.",
            'profile.err_conn': "Serverga ulanishmadi. Local saqlandi.",
            'landing.doc_title': "Messger — Tezkor, Xavfsiz va Zamonaviy Messenger",
            'landing.nav_features': "Imkoniyatlar",
            'landing.nav_demo': "Jonli Demo",
            'landing.nav_about': "Biz haqimizda",
            'landing.app': "Ilova",
            'landing.login': "Kirish",
            'landing.hero_badge': "🚀 Yangi avlod chat tizimi",
            'landing.hero_title_html': "Chegarasiz muloqot va <span class=\"gradient-text\">maksimal xavfsizlik</span>",
            'landing.hero_desc': "Messger yordamida dunyoning istalgan nuqtasidagi yaqinlaringiz bilan real vaqt rejimida bog'laning. End-to-end xavfsizlik va tezkor WebSocket tizimi bilan.",
            'landing.cta_app': "Ilovani ochish",
            'landing.cta_more': "Batafsil ma'lumot",
            'landing.stat_fast_d': "Kechikish",
            'landing.stat_secure_d': "Xavfsiz",
            'landing.stat_open_d': "Manba",
            'landing.feat_title_html': "Nega aynan <span class=\"gradient-text\">Messger</span>?",
            'landing.feat_desc': "Zamonaviy texnologiyalar va qulay interfeys bir joyda",
            'landing.f1_t': "Real-time aloqa",
            'landing.f1_d': "Xabarlar soniyaning ulushlarida yetib boradi, sahifani yangilash shart emas.",
            'landing.f2_t': "Xavfsizlik",
            'landing.f2_d': "Shaxsiy suhbatlaringiz faqat siz va suhbatdoshingiz uchun ochiq.",
            'landing.f3_t': "Media va fayllar",
            'landing.f3_d': "Rasm, video, audio va fayllarni osongina yuboring.",
            'landing.f4_t': "Qulay dizayn",
            'landing.f4_d': "Kunduzgi va tungi rejim, barcha qurilmalarga moslashgan interfeys.",
            'landing.demo_title_html': "Ilova <span class=\"gradient-text\">Interfeysi</span>",
            'landing.demo_desc': "Zamonaviy, tez va qulay messenjer interfeysi",
            'landing.footer_desc': "Messger — zamonaviy texnologiyalar asosida qurilgan qulay va xavfsiz chat ekotizimi.",
            'landing.footer_tech': "Texnologiyalar",
            'landing.footer_stages': "Loyiha bosqichlari",
            'landing.footer_rights': "Barcha huquqlar himoyalangan."
        },
        ru: {
            'common.brand': "Messger",
            'common.loading': "Загрузка…",
            'common.retry': "Повторить",
            'common.copy': "Копировать",
            'common.copied': "Скопировано",
            'common.cancel': "Отмена",
            'common.save': "Сохранить",
            'common.close': "Закрыть",
            'common.language': "Язык",
            'common.error': "Произошла ошибка",

            'nav.home': "Главная",
            'nav.profile': "Профиль",
            'nav.login': "Войти",
            'nav.messages': "Сообщения",

            'open.profile': "Профиль",
            'open.user': "Пользователь",
            'open.group': "Группа",
            'open.channel': "Канал",
            'open.online': "в сети",
            'open.members': "{n} участников",
            'open.message': "Написать сообщение",
            'open.join': "Присоединиться",
            'open.joined': "Вы участник",
            'open.open_chat': "Открыть чат",
            'open.copy_link': "Скопировать ссылку",
            'open.open_in_app': "Открыть в Messger",
            'open.not_found': "Профиль не найден",
            'open.not_found_desc': "Эта ссылка удалена или введена неверно.",
            'open.loading_profile': "Загрузка профиля…",
            'open.back': "Главная",
            'open.about': "Информация",
            'open.link_copied': "Ссылка скопирована",

            'settings.title': "Настройки",
            'settings.night_mode': "Ночной режим",
            'settings.language': "Язык",
            'settings.my_profile': "Мой профиль",
            'settings.new_folder': "Новая папка",
            'settings.new_group': "Новая группа",
            'settings.new_channel': "Новый канал",
            'settings.contacts': "Контакты",

            'app.search': "Поиск",
            'app.message': "Сообщение...",
            'app.manage': "Управление",
            'app.members_title': "Участники и админы",
            'app.new_chat': "Новый чат",

            'auth.back_home': "Вернуться на главную",

            'login.doc_title': "Вход — Messger",
            'login.hero_title': "Снова на связи<br>с друзьями",
            'login.hero_desc': "Быстрые, безопасные и реальные сообщения. С любого устройства ваши друзья всегда рядом.",
            'login.mock1': "Привет! Рад знакомству 🎉",
            'login.mock2': "Взаимно! Сообщения в реальном времени работают ⚡",
            'login.brand_online': "Онлайн",
            'login.brand_free': "Бесплатно",
            'login.brand_safe': "Безопасно",
            'login.welcome': "Добро пожаловать!",
            'login.subtitle': "Войдите в свой аккаунт Messger",
            'login.username': "Имя пользователя или Email",
            'login.username_ph': "Например: sardor_dev",
            'login.password': "Пароль",
            'login.remember': "Запомнить меня",
            'login.forgot': "Забыли пароль?",
            'login.submit': "Войти",
            'login.no_account': "Нет аккаунта?",
            'login.register': "Зарегистрироваться",
            'login.registered_ok': "Вы успешно зарегистрировались! Теперь войдите. 🎉",
            'login.err_fill': "Введите имя пользователя и пароль.",
            'login.err_server': "Не удалось подключиться к серверу. Проверьте, запущен ли Django.",

            'reg.doc_title': "Регистрация — Messger",
            'reg.title': "Регистрация",
            'reg.subtitle': "Войдите в свой аккаунт Messger",
            'reg.password_hint': "минимум 8 символов",
            'reg.hero_title': "Создайте аккаунт<br>и начните общение",
            'reg.hero_desc': "Зарегистрируйтесь за минуту и начните общаться с друзьями в реальном времени.",
            'reg.mock1': "У вас новое сообщение 📩",
            'reg.mock2': "Регистрация занимает 1 минуту ✨",
            'reg.username': "Имя пользователя",
            'reg.email': "Email",
            'reg.optional': "необязательно",
            'reg.email_ph': "email@example.com",
            'reg.password': "Пароль",
            'reg.password_ph': "••••••••",
            'reg.password2': "Повторите пароль",
            'reg.submit': "Зарегистрироваться",
            'reg.have_account': "Уже есть аккаунт?",
            'reg.login': "Войти",
            'reg.err_match': "Пароли не совпадают.",
            'reg.err_short': "Пароль должен содержать не менее 8 символов.",
            'reg.err_server': "Не удалось подключиться к серверу. Проверьте, работает ли Django.",
            'reg.err_default': "Регистрация не удалась.",
            'reg.pw_strength': "Надёжность пароля: ",
            'reg.pw0': "Очень слабый",
            'reg.pw1': "Слабый",
            'reg.pw2': "Средний",
            'reg.pw3': "Хороший",
            'reg.pw4': "Надёжный",

            'join.doc_title': "Присоединиться к группе — Messger",
            'join.channel_fallback': "Канал",
            'join.group_fallback': "Группа",
            'join.meta': "{n} участников · {type}",
            'join.open_group': "Открыть группу",
            'join.join': "Присоединиться",
            'join.request': "Отправить запрос",
            'join.joined_ok': "Вы присоединились ✓",
            'join.sending': "Отправка…",
            'join.request_sent': "Запрос отправлен",
            'join.request_rejected': "Запрос отклонён",
            'join.wait_admin': "Ожидайте подтверждения администратора.",
            'join.private_note': "Приватная группа — присоединитесь после подтверждения.",
            'join.login_join': "Войти и присоединиться",
            'join.login_needed': "Войдите, чтобы присоединиться к группе.",
            'join.bad_link': "Неверная ссылка",
            'join.bad_link_desc': "Код приглашения (code) не найден.",
            'join.not_found': "Не найдено",
            'join.not_found_desc': "Такой группы нет или ссылка устарела.",
            'join.err_join': "Не удалось присоединиться.",
            'join.err_server': "Не удалось подключиться к серверу.",

            'profile.doc_title': "Профиль — Messger",
            'profile.fallback_name': "Пользователь",
            'profile.fallback_username': "пользователь",
            'profile.fallback_bio': "Привет! Я пишу вам в Messger. 🚀",
            'profile.edit': "Редактировать профиль",
            'profile.to_messages': "К сообщениям",
            'profile.copy_link': "Скопировать ссылку",
            'profile.link_copied': "Ссылка на профиль скопирована",
            'profile.copy_hint': "Скопировать ссылку на профиль",
            'profile.email': "Email",
            'profile.last_seen': "Был(а) недавно",
            'profile.chats': "Чаты",
            'profile.chats_n': "{n} бесед",
            'profile.chats_zero': "0 бесед",
            'profile.side_title': "Данные профиля",
            'profile.side_name': "Имя",
            'profile.side_username': "Имя пользователя",
            'profile.side_status': "Статус",
            'profile.online': "Онлайн",
            'profile.account': "Аккаунт",
            'profile.logout': "Выйти",
            'profile.edit_title': "Редактировать профиль",
            'profile.label_name': "Имя",
            'profile.label_bio': "О себе",
            'profile.label_avatar': "Аватар",
            'profile.avatar_ph': "https://... ссылка на изображение",
            'profile.err_name': "Имя не может быть пустым.",
            'profile.saving': "Сохранение...",
            'profile.saved_local': "Не сохранено на сервере. Сохранено локально.",
            'profile.err_conn': "Нет связи с сервером. Сохранено локально.",
            'landing.doc_title': "Messger — Быстрый, безопасный и современный мессенджер",
            'landing.nav_features': "Возможности",
            'landing.nav_demo': "Живое демо",
            'landing.nav_about': "О нас",
            'landing.app': "Приложение",
            'landing.login': "Войти",
            'landing.hero_badge': "🚀 Чат-система нового поколения",
            'landing.hero_title_html': "Общение без границ и <span class=\"gradient-text\">максимальная безопасность</span>",
            'landing.hero_desc': "Общайтесь в реальном времени с близкими из любой точки мира. Со сквозным шифрованием и быстрым WebSocket.",
            'landing.cta_app': "Открыть приложение",
            'landing.cta_more': "Подробнее",
            'landing.stat_fast_d': "Задержка",
            'landing.stat_secure_d': "Безопасно",
            'landing.stat_open_d': "Исходники",
            'landing.feat_title_html': "Почему <span class=\"gradient-text\">Messger</span>?",
            'landing.feat_desc': "Современные технологии и удобный интерфейс в одном месте",
            'landing.f1_t': "Общение в реальном времени",
            'landing.f1_d': "Сообщения приходят за доли секунды, страницу перезагружать не нужно.",
            'landing.f2_t': "Безопасность",
            'landing.f2_d': "Личные переписки видны только вам и вашему собеседнику.",
            'landing.f3_t': "Медиа и файлы",
            'landing.f3_d': "Легко отправляйте фото, видео, аудио и файлы.",
            'landing.f4_t': "Удобный дизайн",
            'landing.f4_d': "Светлая и тёмная темы, интерфейс под все устройства.",
            'landing.demo_title_html': "Интерфейс <span class=\"gradient-text\">приложения</span>",
            'landing.demo_desc': "Современный, быстрый и удобный интерфейс мессенджера",
            'landing.footer_desc': "Messger — удобная и безопасная экосистема чатов на основе современных технологий.",
            'landing.footer_tech': "Технологии",
            'landing.footer_stages': "Этапы проекта",
            'landing.footer_rights': "Все права защищены."
        },
        en: {
            'common.brand': "Messger",
            'common.loading': "Loading…",
            'common.retry': "Retry",
            'common.copy': "Copy",
            'common.copied': "Copied",
            'common.cancel': "Cancel",
            'common.save': "Save",
            'common.close': "Close",
            'common.language': "Language",
            'common.error': "Something went wrong",

            'nav.home': "Home",
            'nav.profile': "Profile",
            'nav.login': "Log in",
            'nav.messages': "Messages",

            'open.profile': "Profile",
            'open.user': "User",
            'open.group': "Group",
            'open.channel': "Channel",
            'open.online': "online",
            'open.members': "{n} members",
            'open.message': "Send message",
            'open.join': "Join",
            'open.joined': "You are a member",
            'open.open_chat': "Open chat",
            'open.copy_link': "Copy link",
            'open.open_in_app': "Open in Messger",
            'open.not_found': "Profile not found",
            'open.not_found_desc': "This link was removed or is incorrect.",
            'open.loading_profile': "Loading profile…",
            'open.back': "Home",
            'open.about': "Info",
            'open.link_copied': "Link copied",

            'settings.title': "Settings",
            'settings.night_mode': "Night Mode",
            'settings.language': "Language",
            'settings.my_profile': "My Profile",
            'settings.new_folder': "New Folder",
            'settings.new_group': "New Group",
            'settings.new_channel': "New Channel",
            'settings.contacts': "Contacts",

            'app.search': "Search",
            'app.message': "Message",
            'app.manage': "Manage",
            'app.members_title': "Members & admins",
            'app.new_chat': "New chat",

            'auth.back_home': "Back to home",

            'login.doc_title': "Log in — Messger",
            'login.hero_title': "Reconnect<br>with your friends",
            'login.hero_desc': "Fast, secure and real-time messages. On any device, your friends are always close.",
            'login.mock1': "Hi! Nice to meet you 🎉",
            'login.mock2': "Likewise! Real-time messages are working ⚡",
            'login.brand_online': "Online",
            'login.brand_free': "Free",
            'login.brand_safe': "Secure",
            'login.welcome': "Welcome back!",
            'login.subtitle': "Sign in to your Messger account",
            'login.username': "Username or Email",
            'login.username_ph': "e.g. sardor_dev",
            'login.password': "Password",
            'login.remember': "Remember me",
            'login.forgot': "Forgot password?",
            'login.submit': "Log in",
            'login.no_account': "Don't have an account?",
            'login.register': "Sign up",
            'login.registered_ok': "Registration successful! Please log in. 🎉",
            'login.err_fill': "Please fill in username and password.",
            'login.err_server': "Could not reach the server. Make sure Django is running.",

            'reg.doc_title': "Sign up — Messger",
            'reg.title': "Sign up",
            'reg.subtitle': "Sign in to your Messger account",
            'reg.password_hint': "at least 8 characters",
            'reg.hero_title': "Create an account<br>start the conversation",
            'reg.hero_desc': "Sign up in a minute and start real-time conversations with your friends.",
            'reg.mock1': "You have a new message 📩",
            'reg.mock2': "Signing up takes 1 minute ✨",
            'reg.username': "Username",
            'reg.email': "Email",
            'reg.optional': "optional",
            'reg.email_ph': "email@example.com",
            'reg.password': "Password",
            'reg.password_ph': "••••••••",
            'reg.password2': "Repeat password",
            'reg.submit': "Sign up",
            'reg.have_account': "Already have an account?",
            'reg.login': "Log in",
            'reg.err_match': "Passwords do not match.",
            'reg.err_short': "Password must be at least 8 characters.",
            'reg.err_server': "Could not reach the server. Make sure Django is running.",
            'reg.err_default': "Registration failed.",
            'reg.pw_strength': "Password strength: ",
            'reg.pw0': "Very weak",
            'reg.pw1': "Weak",
            'reg.pw2': "Medium",
            'reg.pw3': "Good",
            'reg.pw4': "Strong",

            'join.doc_title': "Join group — Messger",
            'join.channel_fallback': "Channel",
            'join.group_fallback': "Group",
            'join.meta': "{n} members · {type}",
            'join.open_group': "Open group",
            'join.join': "Join",
            'join.request': "Send request",
            'join.joined_ok': "Joined ✓",
            'join.sending': "Sending…",
            'join.request_sent': "Request sent",
            'join.request_rejected': "Request rejected",
            'join.wait_admin': "Wait for admin approval.",
            'join.private_note': "Private group — you'll join after admin approval.",
            'join.login_join': "Log in and join",
            'join.login_needed': "Log in to join the group.",
            'join.bad_link': "Invalid link",
            'join.bad_link_desc': "Group invite code not found.",
            'join.not_found': "Not found",
            'join.not_found_desc': "This group doesn't exist or the link has expired.",
            'join.err_join': "Could not join.",
            'join.err_server': "Could not reach the server.",

            'profile.doc_title': "Profile — Messger",
            'profile.fallback_name': "User",
            'profile.fallback_username': "user",
            'profile.fallback_bio': "Hi! I message you on Messger. 🚀",
            'profile.edit': "Edit profile",
            'profile.to_messages': "Go to messages",
            'profile.copy_link': "Copy link",
            'profile.link_copied': "Profile link copied",
            'profile.copy_hint': "Copy profile link",
            'profile.email': "Email",
            'profile.last_seen': "Last seen",
            'profile.chats': "Chats",
            'profile.chats_n': "{n} conversations",
            'profile.chats_zero': "0 conversations",
            'profile.side_title': "Profile details",
            'profile.side_name': "Name",
            'profile.side_username': "Username",
            'profile.side_status': "Status",
            'profile.online': "Online",
            'profile.account': "Account",
            'profile.logout': "Log out",
            'profile.edit_title': "Edit profile",
            'profile.label_name': "Name",
            'profile.label_bio': "Bio",
            'profile.label_avatar': "Avatar",
            'profile.avatar_ph': "https://... image url",
            'profile.err_name': "Name can't be empty.",
            'profile.saving': "Saving...",
            'profile.saved_local': "Not saved on server. Saved locally.",
            'profile.err_conn': "Could not reach server. Saved locally.",
            'landing.doc_title': "Messger — Fast, Secure and Modern Messenger",
            'landing.nav_features': "Features",
            'landing.nav_demo': "Live Demo",
            'landing.nav_about': "About us",
            'landing.app': "Open app",
            'landing.login': "Log in",
            'landing.hero_badge': "🚀 Next-generation chat system",
            'landing.hero_title_html': "Borderless communication and <span class=\"gradient-text\">maximum security</span>",
            'landing.hero_desc': "Chat with your loved ones anywhere in the world in real time. With end-to-end security and a blazing-fast WebSocket.",
            'landing.cta_app': "Open the app",
            'landing.cta_more': "Learn more",
            'landing.stat_fast_d': "Latency",
            'landing.stat_secure_d': "Secure",
            'landing.stat_open_d': "Source",
            'landing.feat_title_html': "Why <span class=\"gradient-text\">Messger</span>?",
            'landing.feat_desc': "Modern tech and a clean interface in one place",
            'landing.f1_t': "Real-time messaging",
            'landing.f1_d': "Messages arrive in split seconds — no page reloads needed.",
            'landing.f2_t': "Security",
            'landing.f2_d': "Your private chats are visible only to you and your peer.",
            'landing.f3_t': "Media & files",
            'landing.f3_d': "Easily send photos, videos, audio and files.",
            'landing.f4_t': "Clean design",
            'landing.f4_d': "Light and dark themes, an interface for every device.",
            'landing.demo_title_html': "App <span class=\"gradient-text\">preview</span>",
            'landing.demo_desc': "A modern, fast and clean messenger interface",
            'landing.footer_desc': "Messger — a convenient and secure chat ecosystem built with modern tech.",
            'landing.footer_tech': "Technologies",
            'landing.footer_stages': "Project stages",
            'landing.footer_rights': "All rights reserved."
        }
    };

    var LANG_NAMES = {
        uz: "O'zbekcha",
        ru: "Русский",
        en: "English"
    };
    var LANG_SHORT = { uz: "UZ", ru: "RU", en: "EN" };

    var SUPPORTED = ['uz', 'ru', 'en'];
    var STORAGE_KEY = 'lang';

    function detectLang() {
        try {
            var saved = localStorage.getItem(STORAGE_KEY);
            if (saved && SUPPORTED.indexOf(saved) !== -1) return saved;
        } catch (e) { /* localStorage yo'q */ }
        var nav = (navigator.language || 'uz').slice(0, 2).toLowerCase();
        return SUPPORTED.indexOf(nav) !== -1 ? nav : 'uz';
    }

    function t(key, vars) {
        var lang = api.lang || 'uz';
        var table = DICT[lang] || DICT.uz;
        var str = table[key];
        if (str == null) str = DICT.uz[key];
        if (str == null) str = key;
        if (vars) {
            str = str.replace(/\{(\w+)\}/g, function (_, k) {
                return vars[k] != null ? vars[k] : '';
            });
        }
        return str;
    }

    function applyI18n(root) {
        root = root || document;
        var nodes = root.querySelectorAll('[data-i18n]');
        for (var i = 0; i < nodes.length; i++) {
            var el = nodes[i];
            var key = el.getAttribute('data-i18n');
            var attr = el.getAttribute('data-i18n-attr');
            if (attr) el.setAttribute(attr, t(key));
            else el.textContent = t(key);
        }
        var htmlNodes = root.querySelectorAll('[data-i18n-html]');
        for (var h = 0; h < htmlNodes.length; h++) {
            htmlNodes[h].innerHTML = t(htmlNodes[h].getAttribute('data-i18n-html'));
        }
        var ph = root.querySelectorAll('[data-i18n-placeholder]');
        for (var j = 0; j < ph.length; j++) {
            ph[j].setAttribute('placeholder', t(ph[j].getAttribute('data-i18n-placeholder')));
        }
        var tt = root.querySelectorAll('[data-i18n-title]');
        for (var k = 0; k < tt.length; k++) {
            tt[k].setAttribute('title', t(tt[k].getAttribute('data-i18n-title')));
        }
        var switches = document.querySelectorAll('[data-set-lang]');
        for (var s = 0; s < switches.length; s++) {
            switches[s].classList.toggle('is-active', switches[s].getAttribute('data-set-lang') === api.lang);
        }
        if (document.documentElement) {
            document.documentElement.setAttribute('lang', api.lang);
        }
    }

    function setLang(lang, opts) {
        if (SUPPORTED.indexOf(lang) === -1) return;
        api.lang = lang;
        try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) { /* ignore */ }
        applyI18n();
        var selects = document.querySelectorAll('[data-lang-select]');
        for (var i = 0; i < selects.length; i++) selects[i].value = lang;
        if (!opts || !opts.silent) {
            document.dispatchEvent(new CustomEvent('langchange', { detail: { lang: lang } }));
        }
    }

    /* Bo'sh .lang-switch bloklarini avtomatik tugmalar bilan to'ldirish */
    function buildSwitches() {
        var boxes = document.querySelectorAll('.lang-switch');
        for (var i = 0; i < boxes.length; i++) {
            var box = boxes[i];
            if (box.getAttribute('data-built') === '1') continue;
            box.setAttribute('data-built', '1');
            box.innerHTML = SUPPORTED.map(function (l) {
                return '<button type="button" class="lang-switch__btn" data-set-lang="' + l + '">' + LANG_SHORT[l] + '</button>';
            }).join('');
        }
    }

    function injectStyles() {
        if (document.getElementById('messger-i18n-style')) return;
        var css = '.lang-switch{display:inline-flex;gap:4px;align-items:center;}' +
            '.lang-switch__btn{background:transparent;border:1px solid rgba(255,255,255,.18);color:inherit;' +
            'font:inherit;font-size:12px;font-weight:700;letter-spacing:.02em;padding:4px 9px;border-radius:8px;' +
            'cursor:pointer;opacity:.65;transition:.15s;}' +
            '.lang-switch__btn:hover{opacity:1;border-color:var(--accent-3,#6ea8ff);}' +
            '.lang-switch__btn.is-active{color:#fff;background:linear-gradient(135deg,var(--accent-1,#6366f1),var(--accent-2,#8b5cf6));border-color:transparent;opacity:1;}';
        var style = document.createElement('style');
        style.id = 'i18n-switch-style';
        style.textContent = css;
        (document.head || document.documentElement).appendChild(style);
    }

    document.addEventListener('click', function (e) {
        var btn = e.target.closest ? e.target.closest('[data-set-lang]') : null;
        if (!btn) return;
        e.preventDefault();
        setLang(btn.getAttribute('data-set-lang'));
    });

    document.addEventListener('change', function (e) {
        if (e.target && e.target.matches && e.target.matches('[data-lang-select]')) {
            setLang(e.target.value);
        }
    });

    var api = {
        lang: detectLang(),
        supported: SUPPORTED,
        names: LANG_NAMES,
        short: LANG_SHORT,
        t: t,
        langName: function (l) { return LANG_NAMES[l] || l; },
        detect: detectLang,
        applyI18n: applyI18n,
        setLang: setLang
    };

    function ready() {
        buildSwitches();
        applyI18n();
        document.documentElement.setAttribute('lang', api.lang);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', ready);
    } else {
        ready();
    }

    window.MESSGER_I18N = api;
})();
