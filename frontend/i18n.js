/* Messger i18n — uz / ru / en.
 *
 * Ishlatish:
 *   <script src="i18n.js"></script>
 *   MESSGER_I18N.t('open.message')
 *   MESSGER_I18N.setLang('ru')
 *   <span data-i18n="open.join"></span>
 *   <input data-i18n-placeholder="login.username">
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

            'settings.title': "Sozlamalar",
            'settings.night_mode': "Tungi rejim",
            'settings.language': "Til",
            'settings.my_profile': "Mening profilim",
            'settings.new_folder': "Yangi papka",
            'settings.new_group': "Yangi guruh",
            'settings.new_channel': "Yangi kanal",
            'settings.contacts': "Kontaktlar"
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

            'settings.title': "Настройки",
            'settings.night_mode': "Ночной режим",
            'settings.language': "Язык",
            'settings.my_profile': "Мой профиль",
            'settings.new_folder': "Новая папка",
            'settings.new_group': "Новая группа",
            'settings.new_channel': "Новый канал",
            'settings.contacts': "Контакты"
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

            'settings.title': "Settings",
            'settings.night_mode': "Night Mode",
            'settings.language': "Language",
            'settings.my_profile': "My Profile",
            'settings.new_folder': "New Folder",
            'settings.new_group': "New Group",
            'settings.new_channel': "New Channel",
            'settings.contacts': "Contacts"
        }
    };

    var LANG_NAMES = {
        uz: "O'zbekcha",
        ru: "Русский",
        en: "English"
    };

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
        var ph = root.querySelectorAll('[data-i18n-placeholder]');
        for (var j = 0; j < ph.length; j++) {
            ph[j].setAttribute('placeholder', t(ph[j].getAttribute('data-i18n-placeholder')));
        }
        var tt = root.querySelectorAll('[data-i18n-title]');
        for (var k = 0; k < tt.length; k++) {
            tt[k].setAttribute('title', t(tt[k].getAttribute('data-i18n-title')));
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

    function langName(code) {
        return LANG_NAMES[code] || code;
    }

    var api = {
        dict: DICT,
        supported: SUPPORTED,
        names: LANG_NAMES,
        lang: detectLang(),
        t: t,
        langName: langName,
        applyI18n: applyI18n,
        setLang: setLang
    };

    window.MESSGER_I18N = api;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { applyI18n(); });
    } else {
        applyI18n();
    }
})();
