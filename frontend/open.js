/* /open/<username> profil sahifasi */
(function () {
    'use strict';

    var API_BASE = (window.MESSGER && window.MESSGER.API_BASE) || '';
    var i18n = window.MESSGER_I18N;

    function getUsername() {
        var path = location.pathname;
        var parts = path.split('/');
        while (parts.length && parts[0] === '') parts.shift();
        if (parts[0] === 'open') {
            var u = parts.slice(1).join('/');
            return u.replace(/\/$/, '').replace(/\.html$/, '');
        }
        var m = location.search.match(/[?&]u=([^&]+)/);
        if (m) return decodeURIComponent(m[1]);
        return '';
    }

    var username = getUsername();
    var card = document.getElementById('openCard');
    var skeleton = document.getElementById('openSkeleton');
    var notFound = document.getElementById('openNotFound');

    var avatar = document.getElementById('openAvatar');
    var name = document.getElementById('openName');
    var handle = document.getElementById('openUsername');
    var badge = document.getElementById('openBadge');
    var about = document.getElementById('openAbout');
    var meta = document.getElementById('openMeta');
    var error = document.getElementById('openError');

    var btnMsg = document.getElementById('openMsgBtn');
    var btnJoin = document.getElementById('openJoinBtn');
    var btnOpen = document.getElementById('openOpenBtn');
    var btnCopy = document.getElementById('openCopyBtn');
    var btnApp = document.getElementById('openAppBtn');
    var hint = document.getElementById('openHint');

    var langBtns = document.querySelectorAll('.lang-switch button');

    function setLangUI() {
        if (!i18n) return;
        var lang = i18n.lang || 'uz';
        langBtns.forEach(function (b) {
            if (b.getAttribute('data-lang') === lang) b.classList.add('is-active');
            else b.classList.remove('is-active');
        });
        if (i18n.applyI18n) i18n.applyI18n();
        document.documentElement.setAttribute('lang', lang);
    }

    if (i18n) {
        setLangUI();
        document.addEventListener('langchange', setLangUI);
    }
    langBtns.forEach(function (b) {
        b.addEventListener('click', function () {
            var l = b.getAttribute('data-lang');
            if (i18n && l) i18n.setLang(l);
        });
    });

    function showCard() {
        card.hidden = false;
        skeleton.hidden = true;
        notFound.hidden = true;
    }
    function showNF() {
        card.hidden = true;
        skeleton.hidden = true;
        notFound.hidden = false;
    }

    function setAvatar(val, fallback) {
        if (val) {
            avatar.textContent = '';
            avatar.style.backgroundImage = 'url(' + val + ')';
            avatar.style.backgroundSize = 'cover';
            avatar.style.backgroundPosition = 'center';
        } else {
            avatar.textContent = (fallback || '?').charAt(0).toUpperCase();
            avatar.style.backgroundImage = 'none';
        }
    }

    function toProfileLink(h) {
        if (!h) return location.href;
        return location.origin + '/open/' + encodeURIComponent(h);
    }

    async function fetchProfile() {
        if (!username) return showNF();
        try {
            var res = await fetch(API_BASE + '/api/public/' + encodeURIComponent(username) + '/');
            if (res.status === 404) return showNF();
            if (!res.ok) throw new Error('bad');
            var data = await res.json();
            render(data);
        } catch (e) {
            showNF();
        }
    }

    function render(data) {
        document.title = (data.display_name || username) + ' — Messger';
        var link = toProfileLink(data.username || username);
        var setMeta = function (id, value) {
            var el = document.getElementById(id);
            if (el) el.setAttribute('content', value);
        };
        setMeta('ogTitle', (data.display_name || username) + ' · @' + (data.username || username) + ' — Messger');
        setMeta('ogDesc', data.about || (i18n && i18n.t ? i18n.t('open.open_in_app') : "Messger'da ochish"));
        if (data.avatar) setMeta('ogImage', data.avatar);
        setMeta('ogUrl', link);
        setMeta('twTitle', (data.display_name || username) + ' — Messger');
        setMeta('twDesc', data.about || '');
        name.textContent = data.display_name || username;
        handle.textContent = '@' + (data.username || username);
        if (i18n && i18n.t) {
            if (data.type === 'channel') badge.textContent = i18n.t('open.channel');
            else if (data.type === 'group') badge.textContent = i18n.t('open.group');
            else badge.textContent = i18n.t('open.user');
        } else {
            if (data.type === 'channel') badge.textContent = 'Kanal';
            else if (data.type === 'group') badge.textContent = 'Guruh';
            else badge.textContent = 'Foydalanuvchi';
        }
        badge.hidden = false;

        setAvatar(data.avatar, data.display_name || data.username);
        about.textContent = data.about || '';
        if (!about.textContent) about.hidden = true; else about.hidden = false;

        var metaStr = '';
        if (data.type === 'user') {
            if (data.is_online) metaStr = (i18n && i18n.t) ? i18n.t('open.online') : 'online';
            else metaStr = '';
        } else {
            var n = data.members_count || 0;
            if (i18n && i18n.t) metaStr = i18n.t('open.members', { n: n });
            else metaStr = n + " a'zo";
        }
        meta.textContent = metaStr;
        if (!metaStr) meta.hidden = true; else meta.hidden = false;

        btnMsg.onclick = function () {
            var access = localStorage.getItem('access');
            var base = location.origin + (location.pathname.indexOf('/open/') !== -1 ? location.pathname.replace(/\/open\/.*/, '') : '');
            if (!access) {
                location.href = 'login.html?next=' + encodeURIComponent('/messenger.html');
                return;
            }
            if (data.type === 'user') {
                location.href = 'messenger.html?user=' + encodeURIComponent(data.username);
            } else {
                location.href = 'messenger.html?chat=' + encodeURIComponent(data.username);
            }
        };

        if (data.type === 'user') {
            btnMsg.hidden = false;
            btnJoin.hidden = true;
            btnOpen.hidden = true;
        } else {
            btnMsg.hidden = true;
            btnJoin.hidden = data.is_member;
            btnOpen.hidden = !data.is_member;
            btnJoin.onclick = function () {
                var code = data.invite_code || data.username;
                location.href = 'join.html?code=' + encodeURIComponent(code);
            };
            btnOpen.onclick = function () {
                var access = localStorage.getItem('access');
                if (!access) {
                    location.href = 'login.html?next=' + encodeURIComponent('/messenger.html?chat=' + encodeURIComponent(data.username));
                    return;
                }
                location.href = 'messenger.html?chat=' + encodeURIComponent(data.username);
            };
        }

        btnCopy.onclick = async function () {
            try {
                var link = toProfileLink(data.username);
                await navigator.clipboard.writeText(link);
                if (i18n && i18n.t) {
                    var prev = btnCopy.textContent;
                    btnCopy.textContent = i18n.t('common.copied');
                    setTimeout(function () { btnCopy.textContent = prev; }, 1200);
                }
            } catch (e) {
                if (error) {
                    error.hidden = false;
                    error.textContent = i18n ? i18n.t('common.error') : 'Xatolik yuz berdi';
                }
            }
        };

        btnApp.onclick = function () {
            var link = toProfileLink(data.username);
            var deep = 'messger://open/' + encodeURIComponent(data.username);
            try {
                location.href = deep;
                setTimeout(function () {
                    location.href = link;
                }, 800);
            } catch (e) {
                location.href = link;
            }
        };

        showCard();
    }

    fetchProfile();
})();
