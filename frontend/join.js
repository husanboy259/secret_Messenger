/* Guruh/kanal join-link sahifasi: join.html?code=... */

const API_BASE = (window.MESSGER && window.MESSGER.API_BASE) || '';
const mediaURL = (u) => (u && u.startsWith('/')) ? API_BASE + u : u;
const T = (k, v) => (window.MESSGER_I18N ? window.MESSGER_I18N.t(k, v) : k);

const $ = (sel) => document.querySelector(sel);

const el = {
    card: $('#joinCard'),
    avatar: $('#joinAvatar'),
    name: $('#joinName'),
    username: $('#joinUsername'),
    about: $('#joinAbout'),
    meta: $('#joinMeta'),
    error: $('#joinError'),
    btn: $('#joinBtn'),
    note: $('#joinNote'),
};

const code = new URLSearchParams(location.search).get('code');
const token = localStorage.getItem('access');

function showError(text) {
    el.error.textContent = text;
    el.error.hidden = false;
}

function initials(name) {
    return (name || '?').trim().charAt(0).toUpperCase() || '?';
}

function setAvatar(chat) {
    if (chat.avatar) {
        el.avatar.textContent = '';
        el.avatar.style.backgroundImage = `url('${mediaURL(chat.avatar)}')`;
    } else {
        el.avatar.textContent = initials(chat.name);
        el.avatar.style.backgroundImage = '';
    }
}

function renderChat(chat) {
    lastChat = chat;
    setAvatar(chat);
    const type = T(chat.is_channel ? 'join.channel_fallback' : 'join.group_fallback');
    el.name.textContent = chat.name || type;
    el.username.textContent = chat.username ? '@' + chat.username : '';
    el.about.textContent = chat.about || '';
    el.meta.textContent = T('join.meta', { n: chat.member_count || 0, type: type });

    if (chat.joined) {
        el.btn.textContent = T('join.open_group');
        el.btn.disabled = false;
        el.btn.classList.remove('join-btn--ghost');
        el.btn.onclick = () => { window.location.href = 'messenger.html'; };
        return;
    }
    if (chat.request === 'pending') {
        el.btn.textContent = T('join.request_sent'); el.btn.disabled = true;
        el.note.textContent = T('join.wait_admin');
        return;
    }
    if (chat.request === 'rejected') {
        el.btn.textContent = T('join.request_rejected'); el.btn.disabled = true;
        return;
    }
    if (chat.is_public) {
        el.btn.textContent = T('join.join'); el.btn.disabled = false;
        el.btn.onclick = () => doJoin();
        return;
    }
    el.btn.textContent = T('join.request'); el.btn.disabled = false;
    el.btn.onclick = () => doJoin();
    el.note.textContent = T('join.private_note');
}

let lastChat = null;
document.addEventListener('langchange', () => { if (lastChat) renderChat(lastChat); });

async function doJoin() {
    el.btn.disabled = true;
    const prev = el.btn.textContent;
    el.btn.textContent = T('join.sending');
    try {
        const res = await fetch(`${API_BASE}/api/chats/${chatId}/join/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: '{}',
        });
        if (res.status === 401) { window.location.href = loginURL(); return; }
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            showError(data.detail || T('join.err_join'));
            el.btn.textContent = prev; el.btn.disabled = false;
            return;
        }
        if (data.joined) {
            el.btn.textContent = T('join.joined_ok');
            window.location.href = 'messenger.html';
            return;
        }
        el.btn.textContent = T('join.request_sent');
        el.note.textContent = T('join.wait_admin');
    } catch (err) {
        showError(T('join.err_server'));
        el.btn.textContent = prev; el.btn.disabled = false;
    }
}

let chatId = null;

function loginURL() {
    const back = encodeURIComponent(location.pathname + location.search);
    return `login.html?next=${back}`;
}

async function load() {
    if (!code) {
        el.name.textContent = T('join.bad_link');
        showError(T('join.bad_link_desc'));
        el.btn.hidden = true;
        return;
    }
    if (!token) {
        el.name.textContent = 'Messger';
        el.about.textContent = T('join.login_needed');
        el.btn.textContent = T('join.login_join');
        el.btn.disabled = false;
        el.btn.onclick = () => { window.location.href = loginURL(); };
        return;
    }
    try {
        const res = await fetch(`${API_BASE}/api/chats/by-invite/${encodeURIComponent(code)}/`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        if (res.status === 401) { window.location.href = loginURL(); return; }
        if (!res.ok) {
            el.name.textContent = T('join.not_found');
            showError(T('join.not_found_desc'));
            el.btn.hidden = true;
            return;
        }
        const chat = await res.json();
        chatId = chat.id;
        renderChat(chat);
    } catch (err) {
        showError(T('join.err_server'));
        el.btn.hidden = true;
    }
}

load();
