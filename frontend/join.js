/* Guruh/kanal join-link sahifasi: join.html?code=... */

const API_BASE = (window.MESSGER && window.MESSGER.API_BASE) || '';
const mediaURL = (u) => (u && u.startsWith('/')) ? API_BASE + u : u;

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
    setAvatar(chat);
    el.name.textContent = chat.name || (chat.is_channel ? 'Kanal' : 'Guruh');
    el.username.textContent = chat.username ? '@' + chat.username : '';
    el.about.textContent = chat.about || '';
    el.meta.textContent = `${chat.member_count || 0} a'zo · ${chat.is_channel ? 'Kanal' : 'Guruh'}`;

    if (chat.joined) {
        el.btn.textContent = "Guruhni ochish";
        el.btn.disabled = false;
        el.btn.classList.remove('join-btn--ghost');
        el.btn.onclick = () => { window.location.href = 'messenger.html'; };
        return;
    }
    if (chat.request === 'pending') {
        el.btn.textContent = "So'rov yuborilgan"; el.btn.disabled = true;
        el.note.textContent = "Admin tasdiqlashini kuting.";
        return;
    }
    if (chat.request === 'rejected') {
        el.btn.textContent = "So'rov rad etilgan"; el.btn.disabled = true;
        return;
    }
    if (chat.is_public) {
        el.btn.textContent = "Qo'shilish"; el.btn.disabled = false;
        el.btn.onclick = () => doJoin();
        return;
    }
    el.btn.textContent = "So'rov yuborish"; el.btn.disabled = false;
    el.btn.onclick = () => doJoin();
    el.note.textContent = "Xususiy guruh — admin tasdiqlagach qo'shilasiz.";
}

async function doJoin() {
    el.btn.disabled = true;
    const prev = el.btn.textContent;
    el.btn.textContent = 'Yuborilmoqda…';
    try {
        const res = await fetch(`${API_BASE}/api/chats/${chatId}/join/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: '{}',
        });
        if (res.status === 401) { window.location.href = loginURL(); return; }
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            showError(data.detail || 'Qo\'shilib bo\'lmadi.');
            el.btn.textContent = prev; el.btn.disabled = false;
            return;
        }
        if (data.joined) {
            el.btn.textContent = 'Qo\'shildingiz ✓';
            window.location.href = 'messenger.html';
            return;
        }
        el.btn.textContent = "So'rov yuborilgan";
        el.note.textContent = 'Admin tasdiqlashini kuting.';
    } catch (err) {
        showError('Serverga ulanib bo\'lmadi.');
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
        el.name.textContent = 'Havola noto\'g\'ri';
        showError('Guruh havolasi (code) topilmadi.');
        el.btn.hidden = true;
        return;
    }
    if (!token) {
        el.name.textContent = 'Messger';
        el.about.textContent = 'Guruhga qo\'shilish uchun tizimga kiring.';
        el.btn.textContent = 'Kirish va qo\'shilish';
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
            el.name.textContent = 'Topilmadi';
            showError('Bunday guruh mavjud emas yoki havola eskirgan.');
            el.btn.hidden = true;
            return;
        }
        const chat = await res.json();
        chatId = chat.id;
        renderChat(chat);
    } catch (err) {
        showError('Serverga ulanib bo\'lmadi.');
        el.btn.hidden = true;
    }
}

load();
