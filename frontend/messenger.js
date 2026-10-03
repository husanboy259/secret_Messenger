/* ==========================================================================
   MESSGER DESKTOP — VANILLA JS, real backend bilan ishlaydi
   (Rad etilgan: Spider-man demo ma'lumotlari. Hammasi /api/* dan keladi.)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', async () => {
    const $ = (sel, root = document) => root.querySelector(sel);
    const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

    /* ─────────────────────────────────────────────────────────────────────
       1. AUTH + API (JWT, refresh, logout)
       ───────────────────────────────────────────────────────────────────── */

    const store = {
        access: localStorage.getItem('access'),
        refresh: localStorage.getItem('refresh'),
        user: (() => { try { return JSON.parse(localStorage.getItem('user') || 'null'); } catch { return null; } })(),
    };

    let refreshing = null;
    async function refreshToken() {
        if (refreshing) return refreshing;
        refreshing = (async () => {
            const res = await fetch('/api/token/refresh/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh: store.refresh }),
            });
            if (!res.ok) throw new Error('refresh-failed');
            const data = await res.json();
            store.access = data.access;
            localStorage.setItem('access', data.access);
        })().finally(() => { refreshing = null; });
        return refreshing;
    }

    /* Deploy bilan mobil: config.js da API_BASE ko'rsatilgan bo'lsa,
       REST so'rovlar o'sha backendga boradi ('' = same-origin). */
    const API_BASE = (window.MESSGER && window.MESSGER.API_BASE) || '';
    const mediaURL = (u) => (u && u.startsWith('/')) ? API_BASE + u : u;

    async function api(path, options = {}) {
        if (!store.access) throw new Error('no-token');
        const isForm = options.body instanceof FormData;
        let res = await fetch(API_BASE + path, {
            ...options,
            headers: {
                ...(isForm ? {} : { 'Content-Type': 'application/json' }),
                'Authorization': `Bearer ${store.access}`,
                ...(options.headers || {}),
            },
        });
        if (res.status === 401 && !options._retry) {
            options._retry = true;
            try { await refreshToken(); }
            catch { loginRedirect(); }
            return api(path, options);
        }
        return res;
    }

    async function apiJSON(path, options) {
        const res = await api(path, options);
        const json = await res.json().catch(() => null);
        if (!res.ok) {
            const raw = json && (json.detail
                || (Array.isArray(json) ? json[0] : null)
                || (json && Object.values(json)[0]));
            const detail = Array.isArray(raw) ? raw[0] : raw;
            throw Object.assign(new Error(String(detail || `Xato (${res.status})`)), { status: res.status, data: json });
        }
        return json;
    }

    function loginRedirect() {
        localStorage.removeItem('access');
        localStorage.removeItem('refresh');
        localStorage.removeItem('user');
        window.location.href = '/login.html';
    }
    if (!store.access) { loginRedirect(); return; }

    /* ─────────────────────────────────────────────────────────────────────
       2. STATE + DOM
       ───────────────────────────────────────────────────────────────────── */

    const state = {
        me: store.user || null,
        folders: [],
        chats: [],
        accounts: [],
        filter: 'all',
        query: '',
        activeChatId: null,
        messages: [],
        replyTo: null,
        socket: null,
        pending: new Map(),      // client_id -> true (optimistik xabarlar)
        pendingAttachment: null, // upload qilingan attachment optimistik xabar uchun
    };

    const dom = {
        app: $('#app'),
        rail: $('#rail'),
        btnMenu: $('#btnMenu'),
        btnBack: $('#btnBack'),
        btnAddChat: $('#btnAddChat'),
        searchInput: $('#searchInput'),
        searchClear: $('#searchClear'),
        chatList: $('#chatList'),
        listEmpty: $('#listEmpty'),
        bannerBirthday: $('#bannerBirthday'),
        stageEmpty: $('#stageEmpty'),
        conv: $('#conv'),
        convBody: $('#convBody'),
        convAvatar: $('#convAvatar'),
        convTitle: $('#convTitle'),
        convStatus: $('#convStatus'),
        convPinned: $('.conv__pinned'),
        convPinnedText: $('.conv__pinned-text'),
        messageList: $('#messageList'),
        messageInput: $('#messageInput'),
        btnSend: $('#btnSend'),
        replyBar: $('#replyBar'),
        replyText: $('#replyText'),
        replyCancel: $('#replyCancel'),
        scrim: $('#scrim'),
        drawer: $('#drawer'),
        btnCollapse: $('#btnCollapse'),
        accountList: $('#accountList'),
        btnAddAccount: $('#btnAddAccount'),
        btnProfile: $('#btnProfile'),
        profileName: $('.profile__name'),
        profileEmoji: $('#profileEmoji'),
        profileStatus: $('.profile__status'),
        btnEmojiStatus: $('#btnEmojiStatus'),
        emojiPop: $('#emojiPop'),
        emojiGrid: $('#emojiGrid'),
        nightSwitch: $('#nightSwitch'),
        btnConvBack: $('#btnConvBack'),
        btnConvMenu: $('#btnConvMenu'),
        toast: $('#toast'),
        railMe: $('#railMe'),
        railAvatar: $('.rail__me .avatar'),
        // Modallar
        addModal: $('#addModal'),
        addModeBtns: $$('#addMode [data-mode]'),
        addNameWrap: $('#addNameWrap'),
        addName: $('#addName'),
        addSearch: $('#addSearch'),
        addResults: $('#addResults'),
        addSelected: $('#addSelected'),
        addCreate: $('#addCreate'),
        addError: $('#addError'),
        contactsModal: $('#contactsModal'),
        contactsList: $('#contactsList'),
        contactsEmpty: $('#contactsEmpty'),
        modalClose: $$('[data-close]'),
        // Biriktirish / ovoz / papka / qo'ng'iroq
        fileInput: $('#fileInput'),
        btnClip: $('#btnClip'),
        btnMic: $('#btnMic'),
        recBar: $('#recBar'),
        recTime: $('#recTime'),
        recStop: $('#recStop'),
        msgInputWrap: $('.composer__row'),
        folderModal: $('#folderModal'),
        folderName: $('#folderName'),
        folderIcons: $('#folderIcons'),
        folderCreate: $('#folderCreate'),
        btnCallVoice: $('#btnCallVoice'),
        btnCallVideo: $('#btnCallVideo'),
        callOverlay: $('#callOverlay'),
        callLocal: $('#callLocal'),
        callRemote: $('#callRemote'),
        callAvatar: $('#callAvatar'),
        callName: $('#callName'),
        callState: $('#callState'),
        callTime: $('#callTime'),
        callMic: $('#callMic'),
        callEnd: $('#callEnd'),
        callSpeaker: $('#callSpeaker'),
        btnCallAccept: $('#btnCallAccept'),
    };

    /* ─────────────────────────────────────────────────────────────────────
       3. UTILS
       ───────────────────────────────────────────────────────────────────── */

    const escapeHTML = (str = '') => String(str).replace(/[&<>'"]/g, t => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
    }[t]));

    const icon = (id, cls = 'ico') => `<svg class="${cls}"><use href="#${id}"/></svg>`;

    const timeAgo = (iso) => {
        if (!iso) return '';
        const d = new Date(iso);
        if (isNaN(d)) return '';
        const now = new Date();
        const same = (a, b) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
        if (same(d, now)) return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
        return `${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}`;
    };

    const initials = (name = '?') => escapeHTML(name.trim().charAt(0).toUpperCase() || '?');

    const avatarHTML = (user, size = 'md') => user && user.avatar
        ? `<span class="avatar avatar--${size}" style="background-image:url('${escapeHTML(mediaURL(user.avatar))}');background-size:cover;background-position:center"></span>`
        : `<span class="avatar avatar--${size}">${initials((user && (user.display_name || user.username)) || '?')}</span>`;

    const chatColor = (chat) => {
        if (chat.is_bot) return '🤖';
        if (chat.is_channel) return '📣';
        const peer = peerOf(chat);
        return peer ? initials((peer.display_name || peer.username)) : initials(chat.title);
    };

    let toastTimer;
    const toast = (message) => {
        dom.toast.textContent = message;
        dom.toast.hidden = false;
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => { dom.toast.hidden = true; }, 2400);
    };

    const scrollBottom = (el) => { el.scrollTop = el.scrollHeight; };
    const autoGrow = (ta) => { ta.style.height = 'auto'; ta.style.height = `${Math.min(ta.scrollHeight, 140)}px`; };

    const peerOf = (chat) => {
        if (!chat.members || chat.type !== 'private') return null;
        return chat.members.find(m => m.id !== state.me?.id) || null;
    };

    const fmtErr = (e) => (e && e.message) || 'Kutilmagan xato.';

    /* ─────────────────────────────────────────────────────────────────────
       4. PROFIL (rail + drawer)
       ───────────────────────────────────────────────────────────────────── */

    function renderProfile() {
        const me = state.me;
        if (!me) return;
        const name = me.display_name || me.username;
        dom.profileName.textContent = name;
        dom.profileEmoji.textContent = me.emoji_status || '💬';
        dom.profileStatus.textContent = me.is_online ? 'online' : 'offline';
        dom.railAvatar.outerHTML = `
            <span class="avatar avatar--sm" id="railAvatar"
                  style="${me.avatar ? `background-image:url('${escapeHTML(mediaURL(me.avatar))}');background-size:cover;background-position:center` : ''}"
                  title="${escapeHTML(name)}">${me.avatar ? '' : initials(name)}</span>`;
        dom.railAvatar = $('#railAvatar');
    }

    /* ─────────────────────────────────────────────────────────────────────
       5. RAIL — papkalar (folders)
       ───────────────────────────────────────────────────────────────────── */

    const SYSTEM_RAIL = [
        { slug: 'all', title: 'All Chats', icon: 'i-chats' },
        { slug: 'favorite', title: 'PC Favorite', icon: 'i-star' },
        { slug: 'bots', title: 'Bots', icon: 'i-bot' },
    ];
    const BOTTOM_RAIL = [
        { slug: 'edit', title: 'Edit', icon: 'i-pencil' },
    ];
    const RESERVED = new Set(['all', 'favorite', 'bots', 'edit']);

    function renderRail() {
        let html = '';
        const ownFolders = (state.folders || []).filter(f => !RESERVED.has(f.slug));
        const items = [...SYSTEM_RAIL, ...ownFolders.map(f => ({ slug: f.slug, title: f.title, icon: f.icon || 'i-folder' })), ...BOTTOM_RAIL];

        $$('.rail__nav', dom.rail).forEach(el => el.remove());

        const nav = document.createElement('div');
        nav.className = 'rail__nav';
        nav.innerHTML = items.map(f => `
            <button class="rail__item${f.slug === state.filter ? ' is-active' : ''}" data-filter="${f.slug}" type="button" title="${escapeHTML(f.title)}">
                ${icon(f.icon)}
                <span class="rail__label">${escapeHTML(f.title)}</span>
            </button>`).join('');
        dom.rail.insertBefore(nav, dom.rail.querySelector('.rail__foot') || null);
    }

    dom.rail.addEventListener('click', (e) => {
        const item = e.target.closest('[data-filter]');
        if (!item) return;
        $$('.rail__item').forEach(i => i.classList.toggle('is-active', i === item));
        state.filter = item.dataset.filter;
        state.activeChatId = null;
        loadChats();
    });

    /* ─────────────────────────────────────────────────────────────────────
       6. CHAT LIST
       ───────────────────────────────────────────────────────────────────── */

    function chatListParams() {
        const p = new URLSearchParams();
        if (state.filter === 'favorite') p.set('favorite', 'true');
        else if (state.filter !== 'edit') p.set('folder', state.filter);
        if (state.query.trim()) p.set('search', state.query.trim());
        return p.toString();
    }

    async function loadChats() {
        try {
            const data = await apiJSON(`/api/chats/${chatListParams() ? '?' + chatListParams() : ''}`);
            state.chats = Array.isArray(data) ? data : (data.results || []);
            state.activeChatId = null;
            clearConv();
            renderChatList();
        } catch (err) {
            toast('Chatlarni yuklab bo\'lmadi: ' + fmtErr(err));
        }
    }

    function clearConv() {
        dom.conv.hidden = true;
        dom.stageEmpty.hidden = false;
        closeSocket();
    }

    function renderChatList() {
        const chats = state.chats;
        if (!chats.length) {
            dom.chatList.innerHTML = '';
            dom.listEmpty.hidden = false;
            return;
        }
        dom.listEmpty.hidden = true;
        const isEditing = state.filter === 'edit';

        dom.chatList.innerHTML = chats.map(chat => {
            const last = chat.last_message;
            const preview = last
                ? `<b>${escapeHTML(last.sender)}:</b> ${escapeHTML(last.content)}`
                : '<span style="opacity:.55">Xabar yo\'q</span>';
            const badge = chat.unread_count
                ? `<span class="badge badge--count chat__badge">${chat.unread_count}</span>`
                : '<span class="chat__badge"></span>';

            return `
            <button class="chat${chat.id === state.activeChatId ? ' is-active' : ''}${isEditing ? ' is-editing' : ''}"
                    type="button" role="option" data-chat-id="${chat.id}">
                <span class="chat__avatar">
                    ${avatarHTML(peerOf(chat), 'md')}
                    ${chat.is_channel ? `<span class="chat__channel-tag">${icon('i-channel', 'ico ico--xs')}</span>` : ''}
                    ${chat.is_bot ? `<span class="chat__channel-tag">🤖</span>` : ''}
                </span>
                <span class="chat__top">
                    <span class="chat__name">${escapeHTML(chat.title)}</span>
                    ${chat.is_channel ? `<span class="chat__verified" style="color:var(--accent-3)">${icon('i-channel', 'ico ico--fill')}</span>` : ''}
                    <span class="chat__time">${timeAgo(last && last.created_at)}</span>
                </span>
                <span class="chat__bottom">
                    ${chat.is_muted ? icon('i-mute', 'ico chat__mute') : ''}
                    <span class="chat__preview">${chat.unread_count ? `<b>${chat.unread_count} ta yangi</b> ${preview}` : preview}</span>
                </span>
                ${isEditing
                    ? `<span class="chat__del" data-del-chat="${chat.id}" title="Chatni o'chirish">${icon('i-trash', 'ico ico--xs')}</span>`
                    : badge}
            </button>`;
        }).join('');
    }

    function openChat(id) {
        const chat = state.chats.find(c => c.id === id);
        if (!chat) return;
        state.activeChatId = id;
        renderChatList();
        renderConversation();
        if (window.matchMedia('(max-width: 900px)').matches) dom.app.classList.add('is-list-hidden');
    }

    dom.chatList.addEventListener('click', (e) => {
        const del = e.target.closest('[data-del-chat]');
        if (del) {
            e.stopPropagation();
            state.filter === 'edit' && deleteChat(Number(del.dataset.delChat));
            return;
        }
        const item = e.target.closest('[data-chat-id]');
        if (item) { openChat(Number(item.dataset.chatId)); return; }
    });

    async function deleteChat(id) {
        try {
            await api(`/api/chats/${id}/`, { method: 'DELETE' });
            toast('Chat o\'chirildi');
            loadChats();
        } catch (err) {
            toast('O\'chirilmadi: ' + fmtErr(err));
        }
    }

    /* ─────────────────────────────────────────────────────────────────────
       7. CONVERSATION (xabarlar + WebSocket)
       ───────────────────────────────────────────────────────────────────── */

    function headerHTML(chat) {
        const peer = peerOf(chat);
        if (chat.is_channel) return { title: chat.title, status: 'Kanal' };
        if (chat.is_bot) return { title: chat.title, status: 'bot' };
        if (peer) return { title: (peer.display_name || peer.username), status: peer.is_online ? 'online' : 'offline' };
        if (chat.type === 'group') return { title: chat.title, status: `${chat.members ? chat.members.length : 0} a\'zo` };
        return { title: chat.title, status: 'suhbat' };
    }

    const REACTION_EMOJI = { like: '👍', love: '❤️', laugh: '😂', sad: '😢' };

    function messageHTML(msg, prev) {
        const out = !!msg.replica || (msg.sender && msg.sender.id === state.me?.id);
        const tail = prev && msg.sender && prev.sender && msg.sender.id === prev.sender.id && !msg.isDeleted && !prev.isDeleted ? ' msg--tail' : '';
        const author = !out && !tail
            ? `<span class="bubble__author">${escapeHTML((msg.sender && (msg.sender.display_name || msg.sender.username)) || '?')}</span>`
            : '';

        const reply = msg.reply_to_detail
            ? (() => {
                let rt = msg.reply_to_detail.content;
                if (!rt && msg.reply_to_detail.attachment && msg.reply_to_detail.attachment.kind) {
                    rt = { image: '📷 Rasm', video: '🎬 Video', audio: '🎵 Ovoz', voice: '🎵 Ovoz', file: '📎 Fayl' }[msg.reply_to_detail.attachment.kind] || '📎 Fayl';
                }
                return `<span class="bubble__reply"><b>${escapeHTML(msg.reply_to_detail.sender ? (msg.reply_to_detail.sender.display_name || msg.reply_to_detail.sender.username) : '')}</b> · ${escapeHTML(rt || '')}</span>`;
            })()
            : '';

        const media = !msg.is_deleted && msg.attachment_detail ? attachmentHTML(msg.attachment_detail) : '';
        const deleted = msg.is_deleted
            ? '<span class="bubble__text bubble--deleted">Bu xabar o\'chirildi</span>'
            : `<span class="bubble__text">${escapeHTML(msg.content)}</span>`;

        const hasMedia = !msg.is_deleted && !!msg.attachment_detail;

        const reactions = (msg.reactions || []).length
            ? `<span class="bubble__reactions">${msg.reactions.map(r => {
                const key = typeof r === 'string' ? r : r.kind;
                const own = typeof r === 'string' ? false : (r.user && r.user.id === state.me?.id);
                return `<span class="reaction${own ? ' is-mine' : ''}">${REACTION_EMOJI[key] || key}</span>`;
            }).join('')}</span>`
            : '';

        const edited = msg.is_edited ? '<span class="bubble__edited">edited</span>' : '';
        const err = msg._error ? '<span class="bubble__error">Yuborilmadi!</span>' : '';
        const canDel = out || (activeChat() && activeChat().my_role === 'admin');

        return `
        <div class="msg msg--${out ? 'out' : 'in'}${tail}" data-msg-id="${msg.id || ''}" data-cid="${escapeHTML(msg.client_id || '')}">
            ${out ? '' : `<span class="msg__avatar">${avatarHTML(msg.sender, 'sm')}</span>`}
            <div class="bubble${hasMedia ? ' has-media' : ''}">
                ${author}${reply}${media}${deleted}${err}
                ${reactions}
                <span class="bubble__foot">
                    ${edited}
                    <span class="bubble__time">${msg._time || timeAgo(msg.created_at)}</span>
                    ${out ? `<span class="bubble__ticks ${msg.is_read ? 'is-read' : ''}">${icon('i-check', 'ico ico--xs' + (msg.is_read ? ' is-read' : ''))}</span>` : ''}
                </span>
            </div>
            ${msg.id ? `<span class="msg__tools">
                <button type="button" data-act="react" title="Reaction">${icon('i-smile', 'ico ico--xs')}</button>
                <button type="button" data-act="reply" title="Reply">${icon('i-reply', 'ico ico--xs')}</button>
                ${canDel ? `<button type="button" data-act="del" title="O'chirish">${icon('i-trash', 'ico ico--xs')}</button>` : ''}
            </span>` : ''}
        </div>`;
    }

    function mediaLabel(msg) {
        if (!msg || !msg.attachment_detail) return '';
        const k = msg.attachment_detail.kind;
        if (k === 'image') return '📷 Rasm';
        if (k === 'video') return '🎬 Video';
        if (k === 'audio' || k === 'voice') return '🎵 Ovoz';
        return '📎 Fayl';
    }

    function attachmentHTML(a) {
        if (!a || !a.url) return '';
        const url = mediaURL(a.url);
        const name = a.file_name || 'fayl';
        if (a.kind === 'image') return `<div class="bubble__media"><img src="${escapeHTML(url)}" alt="${escapeHTML(name)}" loading="lazy"></div>`;
        if (a.kind === 'video') return `<div class="bubble__media"><video src="${escapeHTML(url)}" controls preload="metadata"></video></div>`;
        if (a.kind === 'audio' || a.kind === 'voice') return `<div class="bubble__media"><audio src="${escapeHTML(url)}" controls></audio></div>`;
        return `<div class="bubble__media bubble__file">
            <span class="bubble__file-ico">${icon('i-folder', 'ico')}</span>
            <span>
                <span class="bubble__file-name">${escapeHTML(name)}</span>
                <span class="bubble__file-meta">${a.size ? formatBytes(a.size) : ''}</span>
            </span>
        </div>`;
    }

    const formatBytes = (b) => {
        if (!b) return '';
        if (b < 1024) return b + ' B';
        if (b < 1048576) return (b / 1024).toFixed(1) + ' KB';
        return (b / 1048576).toFixed(1) + ' MB';
    };

    async function loadMessages() {
        const chat = state.chats.find(c => c.id === state.activeChatId);
        if (!chat) return;
        try {
            const data = await apiJSON(`/api/chats/${chat.id}/messages/?limit=100`);
            state.messages = Array.isArray(data) ? data : (data.results || []);
            renderMessageList(true);
        } catch (err) {
            toast('Xabarlar yuklanmadi: ' + fmtErr(err));
        }
    }

    function renderMessageList(scroll = true) {
        dom.messageList.innerHTML = state.messages.map((m, i) => messageHTML(m, i ? state.messages[i - 1] : null)).join('');
        if (scroll) scrollBottom(dom.convBody);
    }

    async function renderConversation() {
        const chat = state.chats.find(c => c.id === state.activeChatId);
        if (!chat) { clearConv(); return; }

        dom.stageEmpty.hidden = true;
        dom.conv.hidden = false;

        const h = headerHTML(chat);
        dom.convAvatar.innerHTML = avatarHTML(peerOf(chat), 'md');
        dom.convTitle.textContent = h.title;
        dom.convStatus.textContent = h.status;
        dom.convStatus.classList.toggle('is-online', h.status === 'online');

        dom.convPinned.hidden = !chat.is_pinned || !chat.pinned_message;
        if (chat.is_pinned && chat.pinned_message) {
            dom.convPinnedText.innerHTML = `Yopish (pin): <b>${escapeHTML(chat.pinned_message.content || '')}</b>`;
        }

        await loadMessages();
        openSocket(chat.id);
        markChatRead(chat.id);
    }

    /* WebSocket */
    const WS_BASE = (window.MESSGER && window.MESSGER.WS_BASE)
        || (location.protocol === 'https:' ? 'wss' : 'ws') + '://' + location.host;

    function openSocket(chatId) {
        closeSocket();
        if (!store.access) return;
        try {
            const ws = new WebSocket(`${WS_BASE}/ws/chat/${chatId}/?token=${encodeURIComponent(store.access)}`);
            state.socket = ws;
            ws.onopen = () => { /* tayyor */ };
            ws.onmessage = (e) => handleSocket(JSON.parse(e.data));
            ws.onclose = (e) => {
                if (e.code === 4401) { loginRedirect(); return; }
                state.socket = null;
                setTimeout(() => { if (state.activeChatId === chatId) openSocket(chatId); }, 2500);
            };
        } catch { /* ws ishlamayapti — REST yetarli */ }
    }

    function closeSocket() {
        if (state.socket) { state.socket.onclose = null; state.socket.close(); state.socket = null; }
    }

    /* Global kanal — boshqa chatlarga kelgan xabarlar ro'yxatni jonli yangilaydi (server
       `/ws/global/` orqali `user_<id>` kanaliga `message.new` yuboradi). */
    let gsocket = null;
    function openGlobalSocket() {
        if (!store.access || gsocket) return;
        try {
            const ws = new WebSocket(`${WS_BASE}/ws/global/?token=${encodeURIComponent(store.access)}`);
            gsocket = ws;
            ws.onmessage = (e) => handleGlobal(JSON.parse(e.data));
            ws.onclose = () => { gsocket = null; setTimeout(openGlobalSocket, 3000); };
        } catch { /* muhim emas */ }
    }

    function handleGlobal(msg) {
        if (!msg || msg.type !== 'notification' || !msg.data) return;
        if (msg.data.event === 'message.new') onRemoteMessage(msg.data);
        else if (msg.data.event === 'chat.deleted') onChatDeleted(msg.data.chat_id);
    }

    function onChatDeleted(chatId) {
        const idx = state.chats.findIndex(c => c.id === chatId);
        if (idx >= 0) state.chats.splice(idx, 1);
        if (state.activeChatId === chatId) {
            state.activeChatId = null;
            clearConv();
        }
        renderChatList();
    }

    async function onRemoteMessage(p) {
        const data = p.message;
        if (!data || !p.chat_id) return;
        if (data.sender && data.sender.id === state.me?.id) return;
        if (p.chat_id === state.activeChatId) { upsertMessage(data); return; }

        let chat = state.chats.find(c => c.id === p.chat_id);
        if (!chat) {
            try { chat = await apiJSON(`/api/chats/${p.chat_id}/`); }
            catch { return; }
            state.chats.unshift(chat);
        }
        const created = data.created_at || new Date().toISOString();
        const last = {
            content: data.is_deleted ? 'Xabar o\'chirildi' : (data.content || mediaLabel(data) || '…'),
            sender: data.sender ? (data.sender.display_name || data.sender.username || '?') : '?',
            created_at: created,
        };
        const oldT = chat.last_message ? Date.parse(chat.last_message.created_at) : 0;
        if (!oldT || Date.parse(created) >= oldT) chat.last_message = last;
        chat.unread_count = (chat.unread_count || 0) + 1;
        renderChatList();
    }

    function handleSocket(msg) {
        if (!msg) return;
        if (msg.type === 'message.new' && msg.data) {
            upsertMessage(msg.data);
        } else if (msg.type === 'typing' && msg.data) {
            if (msg.data.user_id !== state.me?.id) showTyping();
        } else if (msg.type === 'read') {
            renderMessageList(false);
        } else if (msg.type === 'call.signal' && msg.data) {
            handleCallSignal(msg.data);
        }
    }

    /* ─────────────────────────────────────────────────────────────────────
        8b. QO'NG'IROQ — ovoz / video (WebRTC + WS signaling)
       ───────────────────────────────────────────────────────────────────── */

    const ICE = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };
    const call = {
        state: 'idle',      // idle | ringing | connecting | in_call
        kind: 'voice',      // voice | video
        peer: null,
        chatId: null,
        callId: null,
        pc: null,
        localStream: null,
        stream: null,       // o'z oqimi (audio/video mix)
        startAt: null,
        timer: null,
        pending: [],        // kelgan offer dan oldingi ice candidates
        incomingOffer: null,
        ringingTone: null,
        micOn: true,
    };

    function callPeer(chat) {
        if (chat.type !== 'private') return null;
        return chat.members.find(m => m.id !== state.me?.id) || null;
    }

    function activeChat() { return state.chats.find(c => c.id === state.activeChatId) || null; }

    function sendSignal(payload) {
        if (!state.socket || state.socket.readyState !== 1) return toast('Qo\'ng\'iroq uchun WebSocket yo\'q.');
        state.socket.send(JSON.stringify({ action: 'call.signal', payload }));
    }

    async function getUserStream(video) {
        try {
            return await navigator.mediaDevices.getUserMedia({ audio: true, video });
        } catch { return null; }
    }

    function setupCallUI() {
        dom.callRemote.hidden = !!(call.kind !== 'video');
        dom.callLocal.hidden = !!call.kind;
        dom.callTime.hidden = true;
        dom.callOverlay.hidden = false;
        dom.callState.textContent = call.state === 'ringing' ? 'Chaqlash…'
            : call.state === 'connecting' ? 'Ulanish…'
            : 'Qo\'ng\'iroq';
        dom.callAvatar.innerHTML = avatarHTML(call.peer, 'lg');
        dom.callName.textContent = call.peer ? (call.peer.display_name || call.peer.username) : '—';
        dom.btnCallAccept.hidden = !(call.state === 'ringing' && call.incomingOffer);
    }

    async function startCall(kind) {
        if (call.state !== 'idle') return;
        const chat = activeChat();
        const peer = callPeer(chat);
        if (!peer) return toast('Qo\'ng\'iroq faqat shaxsiy chatda ishlaydi.');
        if (!('RTCPeerConnection' in window)) return toast('Bu brauzer WebRTC ni qo\'llamaydi.');

        const stream = await getUserStream(kind === 'video');
        if (!stream) return toast('Mikrofon/kamera yoqilmadi.');

        call.state = 'ringing';
        call.kind = kind;
        call.peer = peer;
        call.chatId = chat.id;
        call.stream = stream;
        setupCallUI();

        call.pc = new RTCPeerConnection(ICE);
        stream.getTracks().forEach(t => call.pc.addTrack(t, stream));
        call.pc.onicecandidate = (e) => {
            if (e.candidate) sendSignal({ type: 'ice', candidate: e.candidate.toJSON(), ser: e.candidate.sdpMLineIndex });
        };
        call.pc.ontrack = (e) => {
            if (!dom.callRemote.srcObject) dom.callRemote.srcObject = new MediaStream();
            dom.callRemote.srcObject.addTrack(e.track);
            if (call.state !== 'in_call' && call.kind === 'video') dom.callRemote.hidden = false;
        };
        call.pc.onconnectionstatechange = () => {
            if (call.pc.connectionState === 'connected') {
                call.state = 'in_call';
                dom.callState.textContent = (call.kind === 'video' ? 'Video ' : '') + 'qo\'ng\'iroq';
            } else if (['failed', 'disconnected', 'closed'].includes(call.pc.connectionState)) {
                endCallUi(true);
            }
        };

        dom.callLocal.srcObject = stream;
        dom.callLocal.muted = true;
        dom.callLocal.play().catch(() => { });

        const offer = await call.pc.createOffer();
        await call.pc.setLocalDescription(offer);
        sendSignal({ type: 'offer', sdp: call.pc.localDescription.toJSON(), to: peer.id, video: kind === 'video' });

        persistCall('started');
        call.startAt = Date.now();
        startTimer();
    }

    function handleCallSignal(data) {
        const meId = state.me?.id;
        if (!data || data.from === meId) return;
        if (data.to && data.to !== meId) return;

        if (call.state === 'idle') {
            if (data.type === 'offer') {
                // kiruvchi qongiroq
                call.state = 'ringing';
                call.kind = data.video ? 'video' : 'voice';
                const chat = activeChat();
                call.peer = chat && callPeer(chat) ? callPeer(chat) : (state.chats.find(c => {
                    const p = callPeer(c);
                    return p && p.id === data.from;
                }) || null);
                call.chatId = chat ? chat.id : null;
                call.incomingOffer = data;
                call.pending = [];
                setupCallUI();
                dom.callState.textContent = 'Chalindi…';
                dom.callTime.hidden = true;
                startRing();
            }
            return;
        }
        if (data.type === 'hangup') { endCallUi(true); return; }

        if (!call.pc) return;

        if (data.type === 'answer' && (call.state === 'ringing' || call.state === 'connecting')) {
            call.state = 'connecting';
            call.pc.setRemoteDescription(data.sdp).then(() => {
                call.pending.forEach(c => call.pc.addIceCandidate(c).catch(() => { }));
                call.pending = [];
                dom.callState.textContent = 'Ulanish…';
            }).catch(() => { });
        } else if (data.type === 'ice') {
            if (call.pc.currentRemoteDescription) call.pc.addIceCandidate(data.candidate).catch(() => { });
            else call.pending.push(data.candidate);
        }
    }

    async function acceptCall() {
        if (!call.incomingOffer) return;
        stopRing();
        const stream = await getUserStream(call.kind === 'video');
        if (!stream) { endCallUi(true); return toast('Mikrofon/kamera yoqilmadi.'); }

        call.stream = stream;
        call.pc = new RTCPeerConnection(ICE);
        stream.getTracks().forEach(t => call.pc.addTrack(t, stream));
        call.pc.onicecandidate = (e) => {
            if (e.candidate) sendSignal({ type: 'ice', candidate: e.candidate.toJSON() });
        };
        call.pc.ontrack = (e) => {
            if (!dom.callRemote.srcObject) dom.callRemote.srcObject = new MediaStream();
            dom.callRemote.srcObject.addTrack(e.track);
            if (call.kind === 'video') dom.callRemote.hidden = false;
        };
        call.pc.onconnectionstatechange = () => {
            if (call.pc.connectionState === 'connected') {
                call.state = 'in_call';
                dom.callState.textContent = (call.kind === 'video' ? 'Video ' : '') + 'qo\'ng\'iroq';
            } else if (['failed', 'disconnected', 'closed'].includes(call.pc.connectionState)) {
                endCallUi(true);
            }
        };

        dom.callLocal.srcObject = stream;
        dom.callLocal.muted = true;
        dom.callLocal.play().catch(() => { });

        try {
            await call.pc.setRemoteDescription(call.incomingOffer.sdp);
            const answer = await call.pc.createAnswer();
            await call.pc.setLocalDescription(answer);
            sendSignal({ type: 'answer', sdp: call.pc.localDescription.toJSON(), to: call.peer.id });
        } catch { endCallUi(true); return; }

        call.pending.forEach(c => call.pc.addIceCandidate(c).catch(() => { }));
        call.pending = [];
        call.state = 'connecting';
        call.incomingOffer = null;
        persistCall('started');
        call.startAt = Date.now();
        dom.callState.textContent = 'Ulanish…';
        startTimer();
    }

    function persistCall(status, duration) {
        if (status === 'started') {
            const chat = activeChat();
            if (!chat) return;
            apiJSON('/api/calls/', {
                method: 'POST',
                body: JSON.stringify({ chat: chat.id, kind: call.kind, status: 'outgoing' }),
            }).then(d => { call.callId = d.id; }).catch(() => { });
        } else if (call.callId) {
            apiJSON(`/api/calls/${call.callId}/`, {
                method: 'PATCH',
                body: JSON.stringify({ status: 'ended', duration: duration || 0 }),
            }).catch(() => { });
        }
    }

    function startTimer() {
        dom.callTime.hidden = false;
        dom.callTime.textContent = '0:00';
        clearInterval(call.timer);
        const tick = () => {
            const secs = Math.floor((Date.now() - call.startAt) / 1000);
            const m = Math.floor(secs / 60);
            const s = secs % 60;
            dom.callTime.textContent = `${m}:${s.toString().padStart(2, '0')}`;
        };
        call.timer = setInterval(tick, 1000);
        tick();
    }

    function endCallLocal() {
        if (call.state === 'idle') return;
        const dur = call.startAt ? Math.floor((Date.now() - call.startAt) / 1000) : 0;
        if (call.state === 'in_call' || call.state === 'connecting') persistCall('completed', dur);
        else persistCall('ended', 0);
        sendSignal({ type: 'hangup', to: call.peer ? call.peer.id : null, reason: 'by_local' });
        endCallUi(false);
    }

    function endCallUi(notified) {
        stopRing();
        if (call.pc) { try { call.pc.close(); } catch { } call.pc = null; }
        if (call.stream) { call.stream.getTracks().forEach(t => t.stop()); call.stream = null; }
        call.localStream = null;
        dom.callLocal.srcObject = null;
        dom.callRemote.srcObject = null;
        clearInterval(call.timer);
        call.timer = null;
        call.startAt = null;
        call.incomingOffer = null;
        call.pending = [];
        call.peer = null;
        call.chatId = null;
        call.callId = null;
        call.state = 'idle';
        if (notified) toast('Qo\'ng\'iroq tugatildi');
        dom.callOverlay.hidden = true;
    }

    function startRing() {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.value = 880;
            gain.gain.value = 0.08;
            osc.connect(gain); gain.connect(ctx.destination);
            osc.start();
            call.ringingTone = { ctx, osc };
            const seq = () => { if (call.ringingTone) { try { osc.frequency.value = 880; } catch { } } };
            call.ringTimer = setInterval(seq, 1200);
            setTimeout(() => { try { gain.gain.value = 0; } catch { } }, 1500);
        } catch { /* qongiroq ovozi o'chirilgan */ }
    }

    function stopRing() {
        if (call.ringingTone) {
            try { call.ringingTone.osc.stop(); call.ringingTone.ctx.close(); } catch { }
            call.ringingTone = null;
        }
        clearInterval(call.ringTimer);
    }

    dom.btnCallVoice.addEventListener('click', () => startCall('voice'));
    dom.btnCallVideo.addEventListener('click', () => startCall('video'));

    dom.callEnd.addEventListener('click', () => endCallLocal());

    dom.callMic.addEventListener('click', () => {
        call.micOn = !call.micOn;
        if (call.stream) call.stream.getAudioTracks().forEach(t => { t.enabled = call.micOn; });
        dom.callMic.classList.toggle('is-on', !call.micOn);
    });

    dom.callSpeaker.addEventListener('click', () => {
        dom.callRemote.muted = !dom.callRemote.muted;
        dom.callSpeaker.classList.toggle('is-on', !dom.callRemote.muted);
    });
    dom.callSpeaker.classList.add('is-on'); // ovoz yoqilgan

    dom.btnCallAccept.addEventListener('click', async (e) => {
        e.stopPropagation();
        await acceptCall();
    });

    function upsertMessage(data) {
        // Optimistik xabar (id=null, client_id bor) bilan server echosi (id bor,
        // client_id ham bor) bir xil xabar — client_id yoki id bo'yicha topamiz.
        const existing = state.messages.findIndex(m => {
            if (data.id && m.id && m.id === data.id) return true;
            if (data.client_id && m.client_id && data.client_id === m.client_id) return true;
            return false;
        });
        if (existing >= 0) {
            state.messages[existing] = { ...state.messages[existing], ...data };
            const el = $(`[data-cid="${data.client_id}"]`) || $(`[data-msg-id="${data.id}"]`);
            if (el) el.outerHTML = messageHTML(state.messages[existing], existing ? state.messages[existing - 1] : null);
        } else {
            state.messages.push(data);
            dom.messageList.insertAdjacentHTML('beforeend', messageHTML(data, state.messages[state.messages.length - 2]));
            scrollBottom(dom.convBody);
        }
        updateChatPreview(state.activeChatId);
    }

    function updateChatPreview(chatId) {
        const chat = state.chats.find(c => c.id === chatId);
        if (!chat || !state.messages.length) return;
        const last = state.messages[state.messages.length - 1];
        chat.last_message = last.is_deleted
            ? { content: 'Xabar o\'chirildi', sender: last.sender ? last.sender.username : '?', created_at: last.created_at }
            : {
                content: last.content || mediaLabel(last) || '…',
                sender: last.sender ? last.sender.username : '?',
                created_at: last.created_at,
            };
        renderChatList();
    }

    /* typing */
    let typingTimeout;
    function showTyping() {
        if ($('#typing-row')) return;
        dom.messageList.insertAdjacentHTML('beforeend', `
            <div class="msg msg--in" id="typing-row">
                <span class="msg__avatar"><span class="avatar avatar--sm">…</span></span>
                <div class="bubble"><span class="typing"><span></span><span></span><span></span></span></div>
            </div>`);
        scrollBottom(dom.convBody);
        clearTimeout(typingTimeout);
        typingTimeout = setTimeout(() => { $('#typing-row')?.remove(); }, 2500);
    }

    /* mark read */
    async function markChatRead(chatId) {
        try { await apiJSON(`/api/chats/${chatId}/read/`, { method: 'POST', body: '{}' }); }
        catch { /* muhim emas */ }
        if (state.socket && state.socket.readyState === 1) {
            const last = state.messages[state.messages.length - 1];
            if (last && last.id) state.socket.send(JSON.stringify({ action: 'read', message_id: last.id }));
        }
        const chat = state.chats.find(c => c.id === chatId);
        if (chat) { chat.unread_count = 0; }
        renderChatList();
    }

    /* ─────────────────────────────────────────────────────────────────────
       8. COMPOSER — yuborish / reply / react / delete
       ───────────────────────────────────────────────────────────────────── */

    dom.messageInput.addEventListener('input', () => {
        autoGrow(dom.messageInput);
        if (state.socket && state.socket.readyState === 1 && dom.messageInput.value.trim()) {
            state.socket.send(JSON.stringify({ action: 'typing', is_typing: true }));
        }
    });

    dom.messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    dom.btnSend.addEventListener('click', sendMessage);

    async function sendMessage() {
        const text = dom.messageInput.value.trim();
        const attachment = state.pendingAttachment || null;
        if (!text && !attachment) return;
        const chat = state.chats.find(c => c.id === state.activeChatId);
        if (!chat) return;

        const clientId = crypto.randomUUID();
        const optimistic = {
            id: null,
            client_id: clientId,
            chat: chat.id,
            sender: state.me,
            content: text,
            is_deleted: false,
            is_edited: false,
            is_read: false,
            created_at: new Date().toISOString(),
            replies: [],
            reactions: [],
            attachment_detail: attachment || null,
            reply_to_detail: state.replyTo ? { sender: { display_name: 'You' }, content: state.replyTo.text } : null,
            replica: true,
            _time: timeAgo(new Date().toISOString()),
        };

        state.messages.push(optimistic);
        dom.messageInput.value = '';
        autoGrow(dom.messageInput);
        dom.replyBar.hidden = true;
        state.pendingAttachment = null;
        dom.messageList.insertAdjacentHTML('beforeend', messageHTML(optimistic, state.messages[state.messages.length - 2]));
        scrollBottom(dom.convBody);

        const replyTo = state.replyTo ? state.replyTo.id : null;
        state.replyTo = null;

        // 1) WebSocket orqali (server saqlaydi va guruhga broadcast qiladi)
        if (state.socket && state.socket.readyState === 1) {
            state.socket.send(JSON.stringify({
                action: 'message.create', text, reply_to: replyTo, client_id: clientId,
                attachment_id: attachment ? attachment.id : null,
            }));
            return;
        }
        // 2) WS bo'lmasa REST zaxira
        try {
            const created = await apiJSON(`/api/chats/${chat.id}/messages/`, {
                method: 'POST',
                body: JSON.stringify({ content: text, reply_to: replyTo, client_id: clientId, attachment: attachment ? attachment.id : null }),
            });
            upsertMessage({ ...created, client_id: clientId });
        } catch (err) {
            optimistic._error = true;
            renderMessageList(false);
            toast('Yuborilmadi: ' + fmtErr(err));
        }
    }

    /* Biriktirish (clip) va ovozli xabar */
    async function uploadAttachment(file, kind) {
        const form = new FormData();
        form.append('file', file);
        form.append('kind', kind);
        const att = await apiJSON('/api/uploads/', { method: 'POST', body: form });
        return att;
    }

    function kindForFile(file) {
        if (file.type.startsWith('image/')) return 'image';
        if (file.type.startsWith('video/')) return 'video';
        if (file.type.startsWith('audio/')) return 'audio';
        return 'file';
    }

    async function sendFile(file) {
        if (!file.type.startsWith('image/')) {
            try {
                const kind = file.type.startsWith('video/') ? 'video'
                    : file.type.startsWith('audio/') ? 'audio' : 'file';
                const att = await uploadAttachment(file, kind);
                state.pendingAttachment = att;
                sendMessage();
                dom.messageInput.focus();
            } catch (err) {
                toast('Yuklanmadi: ' + fmtErr(err));
            }
            return;
        }
        try {
            const att = await uploadAttachment(file, 'image');
            state.pendingAttachment = att;
            sendMessage();
            dom.messageInput.focus();
        } catch (err) {
            toast('Yuklanmadi: ' + fmtErr(err));
        }
    }

    dom.btnClip.addEventListener('click', () => dom.fileInput.click());
    dom.fileInput.addEventListener('change', () => {
        const file = dom.fileInput.files && dom.fileInput.files[0];
        if (file) sendFile(file);
        dom.fileInput.value = '';
    });

    /* MediaRecorder — ovozli xabar */
    let recorder = null;
    let recChunks = [];
    let recTimer = null;
    let recSeconds = 0;

    dom.btnMic.addEventListener('click', async () => {
        // Yozish davom etayotganda bosilsa — to'xtatadi (record o'chadi)
        if (recorder && recorder.state === 'recording') { recorder.stop(); return; }
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            recorder = new MediaRecorder(stream);
            recChunks = [];
            recorder.ondataavailable = (e) => { if (e.data.size) recChunks.push(e.data); };
            recorder.onstop = async () => {
                const blob = new Blob(recChunks, { type: recorder.mimeType || 'audio/webm' });
                stream.getTracks().forEach(t => t.stop());
                hideRecBar();
                if (!blob.size) { toast('Ovoz yozilmadi.'); return; }
                try {
                    const att = await uploadAttachment(new File([blob], 'voice.webm', { type: blob.type }), 'voice');
                    state.pendingAttachment = att;
                    sendMessage();
                } catch (err) { toast('Yuklanmadi: ' + fmtErr(err)); }
            };
            recorder.start();
            recSeconds = 0;
            showRecBar();
        } catch { toast('Mikrofon yoqilmadi.'); }
    });

    function setMicRecording(on) {
        dom.btnMic.classList.toggle('is-rec', on);
        dom.btnMic.title = on ? "To'xtatish (record o'chirish)" : 'Ovozli xabar';
        const use = dom.btnMic.querySelector('use');
        if (use) use.setAttribute('href', on ? '#i-close' : '#i-mic');
    }

    function showRecBar() {
        dom.recBar.hidden = false;
        dom.recTime.textContent = '0:00';
        setMicRecording(true);
        recTimer = setInterval(() => {
            recSeconds++;
            const m = Math.floor(recSeconds / 60);
            const s = recSeconds % 60;
            dom.recTime.textContent = `${m}:${s.toString().padStart(2, '0')}`;
        }, 1000);
    }

    function hideRecBar() {
        dom.recBar.hidden = true;
        clearInterval(recTimer);
        recTimer = null;
        setMicRecording(false);
    }

    dom.recStop.addEventListener('click', () => {
        if (recorder && recorder.state === 'recording') recorder.stop();
        else hideRecBar();
    });

    /* Reply */
    dom.messageList.addEventListener('dblclick', (e) => {
        const wrap = e.target.closest('[data-msg-id]');
        const msg = state.messages.find(m => m.id === Number(wrap?.dataset.msgId));
        if (!msg || msg.is_deleted) return;
        setReply(msg);
    });

    dom.messageList.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-act]');
        const wrap = e.target.closest('[data-msg-id]');
        const msg = state.messages.find(m => m.id === Number(wrap?.dataset.msgId));
        if (!btn || !msg) return;
        if (btn.dataset.act === 'reply') setReply(msg);
        if (btn.dataset.act === 'react') toggleReaction(msg);
        if (btn.dataset.act === 'del') deleteMessage(msg);
    });

    async function deleteMessage(msg) {
        if (!msg.id) return;
        const removeLocal = () => {
            msg.is_deleted = true;
            msg.content = '';
            msg.attachment_detail = null;
            renderMessageList(false);
            updateChatPreview(state.activeChatId);
        };
        if (state.socket && state.socket.readyState === 1) {
            state.socket.send(JSON.stringify({ action: 'message.delete', message_id: msg.id }));
            removeLocal();
            return;
        }
        try {
            await api(`/api/messages/${msg.id}/`, { method: 'DELETE' });
            removeLocal();
        } catch (err) {
            toast('O\'chirilmadi: ' + fmtErr(err));
        }
    }

    /* Conv header menyusi — chat / kanalni o'chirish */
    let convMenuEl = null;
    function closeConvMenu() {
        if (convMenuEl) { convMenuEl.remove(); convMenuEl = null; }
    }
    function openConvMenu() {
        const chat = activeChat();
        if (!chat) return;
        closeConvMenu();
        const r = dom.btnConvMenu.getBoundingClientRect();
        const label = chat.is_channel ? 'Kanalni o\'chirish' : 'Chatni o\'chirish';
        convMenuEl = document.createElement('div');
        convMenuEl.style.cssText = 'position:fixed;top:' + (r.bottom + 8) + 'px;right:16px;z-index:1300;min-width:230px;background:var(--panel,#fff);border:1px solid var(--line,#e4e8ec);border-radius:14px;box-shadow:0 8px 24px rgba(0,0,0,.18);padding:6px;display:flex;flex-direction:column;gap:2px;';
        convMenuEl.innerHTML = `
            <button type="button" data-cm="del" style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:0;background:none;border-radius:10px;font:inherit;cursor:pointer;text-align:left;color:var(--danger,#e5484d);">${icon('i-trash', 'ico ico--sm')}<span>${label}</span></button>`;
        document.body.appendChild(convMenuEl);
        convMenuEl.addEventListener('click', (e) => {
            const b = e.target.closest('[data-cm]');
            if (!b) return;
            closeConvMenu();
            if (b.dataset.cm === 'del') confirmDeleteChat(chat);
        });
    }
    function confirmDeleteChat(chat) {
        if (!confirm(`"${chat.title}" ${chat.is_channel ? 'kanali' : 'chati'} barcha uchun o'chirilsinmi?`)) return;
        deleteChat(chat.id);
    }
    dom.btnConvMenu.addEventListener('click', (e) => {
        e.stopPropagation();
        if (convMenuEl) closeConvMenu();
        else openConvMenu();
    });
    document.addEventListener('click', (e) => {
        if (convMenuEl && !convMenuEl.contains(e.target) && e.target !== dom.btnConvMenu) closeConvMenu();
    });

    function setReply(msg) {
        state.replyTo = { id: msg.id, text: msg.content, author: msg.sender ? (msg.sender.display_name || msg.sender.username) : '?' };
        dom.replyText.textContent = `${state.replyTo.author}: ${msg.content}`;
        dom.replyBar.hidden = false;
        dom.messageInput.focus();
    }

    dom.replyCancel.addEventListener('click', () => {
        state.replyTo = null;
        dom.replyBar.hidden = true;
    });

    async function toggleReaction(msg) {
        if (!msg.id) return;
        const pool = ['like', 'love', 'laugh', 'sad'];
        const kind = pool[Math.floor(Math.random() * pool.length)];
        try {
            const data = await apiJSON(`/api/messages/${msg.id}/react/`, { method: 'POST', body: JSON.stringify({ kind }) });
            msg.reactions = data.reactions || [];
            const idx = state.messages.findIndex(m => m.id === msg.id);
            const el = $(`[data-msg-id="${msg.id}"]`);
            if (el && idx >= 0) el.outerHTML = messageHTML(state.messages[idx], idx ? state.messages[idx - 1] : null);
        } catch (err) {
            toast('Reaction qo\'shilmadi: ' + fmtErr(err));
        }
    }

    /* ─────────────────────────────────────────────────────────────────────
       9. ADD CHAT — username bilan qo'shilish (private / group / channel)
       ───────────────────────────────────────────────────────────────────── */

    let addMode = 'private';
    let selectedUsers = [];
    let searchTimer;

    function openAddChat(mode = 'private') {
        addMode = mode;
        selectedUsers = [];
        dom.addName.value = '';
        dom.addSearch.value = '';
        dom.addResults.innerHTML = '';
        dom.addError.style.display = 'none';
        dom.addCreate.disabled = (mode === 'private');
        renderAddMode();
        renderSelected();
        dom.addModal.hidden = false;
        if (mode === 'private') dom.addSearch.focus();
        else dom.addName.focus();
    }

    function closeAddChat() {
        dom.addModal.hidden = true;
        if (!dom.addName.value.trim()) dom.addNameWrap.hidden = true;
    }

    function renderAddMode() {
        dom.addModeBtns.forEach(b => b.classList.toggle('is-active', b.dataset.mode === addMode));
        const needsName = addMode !== 'private';
        dom.addNameWrap.hidden = !needsName;
        dom.addName.placeholder = addMode === 'channel' ? 'Kanal nomi' : 'Guruh nomi';
        dom.addCreate.disabled = addMode === 'private' && selectedUsers.length === 0;
        dom.addCreate.querySelector('.add-create-label').textContent =
            addMode === 'channel' ? 'Kanal yaratish' : (addMode === 'group' ? 'Guruh yaratish' : 'Chatni boshlash');
    }

    function renderSelected() {
        dom.addSelected.innerHTML = selectedUsers.map(u => `
            <span class="chip" data-remove-id="${u.id}">
                ${escapeHTML(u.display_name || u.username)}
                <span class="chip__x">${icon('i-close', 'ico ico--xs')}</span>
            </span>`).join('');
        dom.addCreate.disabled = selectedUsers.length === 0;
        if (addMode === 'private') dom.addCreate.textContent = 'Chatni boshlash';
    }

    function renderAddResults(users) {
        dom.addResults.innerHTML = users.map(u => `
            <button class="user-row" data-user-id="${u.id}" type="button">
                ${avatarHTML(u, 'md')}
                <span class="user-row__body">
                    <span class="user-row__name">${escapeHTML(u.display_name || u.username)}</span>
                    <span class="user-row__sub">@${escapeHTML(u.username)}</span>
                </span>
                <span class="user-row__act">${icon('i-plus', 'ico')}</span>
            </button>`).join('') || '<p class="add-none">Foydalanuvchi topilmadi.</p>';
        dom.addCreate.disabled = selectedUsers.length === 0;
        if (addMode !== 'private') dom.addCreate.disabled = selectedUsers.length === 0;
    }

    async function searchUsers(query) {
        if (!query.trim()) { dom.addResults.innerHTML = ''; return; }
        try {
            const data = await apiJSON(`/api/users/?search=${encodeURIComponent(query.trim())}`);
            const users = (Array.isArray(data) ? data : (data.results || []))
                .filter(u => u.id !== state.me?.id && !selectedUsers.some(s => s.id === u.id));
            renderAddResults(users);
        } catch (err) {
            dom.addResults.innerHTML = `<p class="add-none">Qidiruv ishlamadi: ${escapeHTML(fmtErr(err))}</p>`;
        }
    }

    dom.addSearch.addEventListener('input', () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => searchUsers(dom.addSearch.value), 300);
    });

    dom.addResults.addEventListener('click', (e) => {
        const row = e.target.closest('[data-user-id]');
        if (!row) return;
        const id = Number(row.dataset.userId);
        const user = { id };
        try { /* nomini serverdan olamiz — id yetsa bo'ladi */ }
        catch { }
        selectedUsers.push(user);
        if (addMode === 'private') {
            createChat([id]);
            return;
        }
        dom.addSearch.value = '';
        renderSelected();
    });

    dom.addSelected.addEventListener('click', (e) => {
        const chip = e.target.closest('[data-remove-id]');
        if (!chip) return;
        selectedUsers = selectedUsers.filter(u => u.id !== Number(chip.dataset.removeId));
        renderSelected();
        dom.addResults.innerHTML = '';
    });

    dom.addCreate.addEventListener('click', () => {
        if (addMode === 'private') {
            if (selectedUsers.length) createChat([selectedUsers[0].id]);
            return;
        }
        const name = dom.addName.value.trim();
        if (!name) { dom.addError.textContent = (addMode === 'channel' ? 'Kanal' : 'Guruh') + ' nomi kerak.'; dom.addError.style.display = 'block'; return; }
        if (!selectedUsers.length) { dom.addError.textContent = 'Kamida bitta foydalanuvchi qo\'shing.'; dom.addError.style.display = 'block'; return; }
        createChat(selectedUsers.map(u => u.id), { name, is_channel: addMode === 'channel', type: 'group' });
    });

    async function createChat(memberIds, extra = {}) {
        const isChannel = extra.is_channel || addMode === 'channel';
        if (!memberIds.length) return;
        dom.addCreate.disabled = true;
        try {
            const chat = await apiJSON('/api/chats/', {
                method: 'POST',
                body: JSON.stringify({
                    type: isChannel ? 'group' : (extra.type || 'private'),
                    member_ids: memberIds,
                    ...(extra.name ? { name: extra.name } : {}),
                    ...(isChannel ? { is_channel: true } : {}),
                }),
            });
            closeAddChat();
            toast(isChannel ? 'Kanal yaratildi' : 'Yangi chat boshlandi');
            await loadChats();
            openChat(chat.id);
        } catch (err) {
            // Shu suhbat allaqachon mavjud — topib ochamiz
            if (err.message.includes('allaqachon mavjud') && !isChannel) {
                const data = await apiJSON('/api/chats/').catch(() => []);
                const list = data.results || data;
                const existing = list.find(c => {
                    const peer = peerOf(c);
                    return peer && memberIds.includes(peer.id);
                });
                if (existing) {
                    closeAddChat();
                    await loadChats();
                    openChat(existing.id);
                    return;
                }
            }
            dom.addError.textContent = 'Yaratilmadi: ' + fmtErr(err);
            dom.addError.style.display = 'block';
        } finally {
            dom.addCreate.disabled = false;
        }
    }

    /* ─────────────────────────────────────────────────────────────────────
       10. CONTACTS MODAL
       ───────────────────────────────────────────────────────────────────── */

    async function openContacts() {
        dom.contactsList.innerHTML = '';
        dom.contactsEmpty.hidden = true;
        dom.contactsModal.hidden = false;
        try {
            const data = await apiJSON('/api/contacts/');
            const items = data.results || (Array.isArray(data) ? data : []);
            dom.contactsEmpty.hidden = items.length > 0;
            dom.contactsList.innerHTML = items.map(c => `
                <div class="user-row">
                    ${avatarHTML(c.user, 'md')}
                    <span class="user-row__body">
                        <span class="user-row__name">${escapeHTML(c.user.display_name || c.user.username)}</span>
                        <span class="user-row__sub">@${escapeHTML(c.user.username)}</span>
                    </span>
                    <button class="user-row__act" data-contact-user="${c.user.id}" title="Xabar">${icon('i-send', 'ico')}</button>
                </div>`).join('');
        } catch (err) {
            dom.contactsList.innerHTML = `<p class="add-none">Kontaktlar ishlamadi: ${escapeHTML(fmtErr(err))}</p>`;
        }
    }

    dom.contactsList.addEventListener('click', async (e) => {
        const btn = e.target.closest('[data-contact-user]');
        if (!btn) return;
        dom.contactsModal.hidden = true;
        const memberIds = [Number(btn.dataset.contactUser)];
        const chat = await apiJSON('/api/chats/', { method: 'POST', body: JSON.stringify({ type: 'private', member_ids: memberIds }) })
            .catch(async (err) => {
                if (String(err.message).includes('allaqachon mavjud')) {
                    const data = await apiJSON('/api/chats/').catch(() => ({ results: [] }));
                    const list = data.results || data || [];
                    return list.find(c => { const p = peerOf(c); return p && p.id === memberIds[0]; }) || null;
                }
                toast('Chat ochilmadi: ' + fmtErr(err));
                return null;
            });
        if (chat) { await loadChats(); openChat(chat.id); }
    });

    /* ─────────────────────────────────────────────────────────────────────
       11. DRAWER
       ───────────────────────────────────────────────────────────────────── */

    const setDrawer = (open) => {
        dom.drawer.classList.toggle('is-open', open);
        dom.drawer.setAttribute('aria-hidden', String(!open));
        dom.scrim.hidden = !open;
        dom.btnMenu.setAttribute('aria-expanded', String(open));
        if (open) dom.btnCollapse.focus({ preventScroll: true });
    };
    const isDrawerOpen = () => dom.drawer.classList.contains('is-open');

    dom.btnMenu.addEventListener('click', () => setDrawer(true));
    dom.scrim.addEventListener('click', () => setDrawer(false));
    dom.railMe.addEventListener('click', () => setDrawer(true));

    dom.btnCollapse.addEventListener('click', () => {
        dom.drawer.classList.toggle('is-collapsed');
        localStorage.setItem('messger-drawer', dom.drawer.classList.contains('is-collapsed') ? 'collapsed' : 'open');
    });

    dom.btnProfile.addEventListener('click', () => { setDrawer(false); window.location.href = '/profile.html'; });

    $('#drawerMenu').addEventListener('click', async (e) => {
        const item = e.target.closest('[data-route]');
        if (!item) return;
        const route = item.dataset.route;
        setDrawer(false);
        if (route === 'profile') window.location.href = '/profile.html';
        else if (route === 'new-folder') openFolderModal();
        else if (route === 'new-group') openAddChat('group');
        else if (route === 'new-channel') openAddChat('channel');
        else if (route === 'contacts') openContacts();
        else if (route === 'settings') window.location.href = '/profile.html';
    });

    /* Papka yaratish */
    let folderIcon = 'i-folder';

    function openFolderModal() {
        dom.folderName.value = '';
        folderIcon = 'i-folder';
        dom.folderIcons.querySelectorAll('.chip').forEach(c => c.classList.toggle('is-active', c.dataset.icon === folderIcon));
        dom.folderModal.hidden = false;
        dom.folderName.focus();
    }

    dom.folderIcons.addEventListener('click', (e) => {
        const chip = e.target.closest('.chip');
        if (!chip) return;
        folderIcon = chip.dataset.icon;
        dom.folderIcons.querySelectorAll('.chip').forEach(c => c.classList.toggle('is-active', c === chip));
    });

    dom.folderCreate.addEventListener('click', async () => {
        const title = dom.folderName.value.trim();
        if (!title) { toast('Papka nomini kiriting!'); dom.folderName.focus(); return; }
        dom.folderCreate.disabled = true;
        try {
            const created = await apiJSON('/api/folders/', {
                method: 'POST',
                body: JSON.stringify({ title, icon: folderIcon }),
            });
            state.folders.push(created);
            renderRail();
            dom.folderModal.hidden = true;
            toast('Papka yaratildi ✓');
            state.filter = created.slug;
            $$('.rail__item').forEach(i => i.classList.toggle('is-active', i.dataset.filter === created.slug));
            await loadChats();
        } catch (err) {
            toast('Yaratilmadi: ' + fmtErr(err));
        } finally {
            dom.folderCreate.disabled = false;
        }
    });

    dom.btnAddAccount.addEventListener('click', () => window.location.href = '/login.html');

    /* Accounts switcher */
    async function loadAccounts() {
        try {
            const data = await apiJSON('/api/accounts/');
            state.accounts = data.results || (Array.isArray(data) ? data : []);
        } catch { state.accounts = []; }
        renderAccounts();
    }

    function renderAccounts() {
        const me = state.me;
        const items = state.accounts.length ? state.accounts : [{ id: 0, name: me ? (me.display_name || me.username) : '?', sub: me ? (me.email || me.username) : '', emoji: me?.emoji_status || '💬', unread: 0, is_active: true }];
        dom.accountList.innerHTML = items.map(a => `
            <button class="account${a.is_active ? ' is-active' : ''}" type="button" role="tab" data-account-id="${a.id}">
                <span class="account__ico"><span class="avatar avatar--sm avatar--emoji avatar--lg-emoji">${escapeHTML(a.emoji || '👤')}</span></span>
                <span class="account__body">
                    <span class="account__name">${escapeHTML(a.name)}</span>
                    <span class="account__sub">${escapeHTML(a.sub)}</span>
                </span>
                <span class="account__unread" ${a.unread ? '' : 'hidden'}>${a.unread}</span>
            </button>`).join('');
    }

    dom.accountList.addEventListener('click', async (e) => {
        const btn = e.target.closest('[data-account-id]');
        if (!btn) return;
        const id = Number(btn.dataset.accountId);
        const active = state.accounts.find(a => a.is_active);
        if (id && active && id !== active.id) {
            try {
                await apiJSON(`/api/accounts/${id}/activate/`, { method: 'POST', body: '{}' });
                toast('Account almashtirildi');
                await loadAccounts();
            } catch (err) {
                toast('Almashtirilmadi: ' + fmtErr(err));
            }
        }
    });

    /* ─────────────────────────────────────────────────────────────────────
       12. EMOJI STATUS
       ───────────────────────────────────────────────────────────────────── */

    const EMOJIS = ['🔥', '⚡', '🚀', '💜', '⚽', '🎯', '🌈', '😎', '🎧', '🧠', '☕', '🌙', '⭐', '🏆', '🎨', '🐍'];

    dom.btnEmojiStatus.addEventListener('click', (e) => {
        e.stopPropagation();
        dom.emojiPop.hidden = !dom.emojiPop.hidden;
        if (!dom.emojiPop.hidden) {
            const r = dom.btnEmojiStatus.getBoundingClientRect();
            dom.emojiPop.style.top = `${Math.min(r.bottom + 8, window.innerHeight - 190)}px`;
            dom.emojiPop.style.left = `${Math.max(10, Math.min(r.left, window.innerWidth - 260))}px`;
        }
    });
    dom.emojiGrid.innerHTML = EMOJIS.map(e => `<button type="button" data-emoji="${e}">${e}</button>`).join('');
    dom.emojiGrid.addEventListener('click', async (e) => {
        const btn = e.target.closest('[data-emoji]');
        if (!btn) return;
        dom.emojiPop.hidden = true;
        if (state.me) state.me.emoji_status = btn.dataset.emoji;
        dom.profileEmoji.textContent = btn.dataset.emoji;
        try { await apiJSON('/api/users/me/', { method: 'PATCH', body: JSON.stringify({ emoji_status: btn.dataset.emoji }) }); }
        catch { /* localStorage bilan ham ishlaydi */ }
        toast(`Emoji status: ${btn.dataset.emoji}`);
    });
    document.addEventListener('click', (e) => {
        if (dom.emojiPop.hidden) return;
        if (!dom.emojiPop.contains(e.target) && !dom.btnEmojiStatus.contains(e.target)) dom.emojiPop.hidden = true;
    });

    /* ─────────────────────────────────────────────────────────────────────
       13. THEME (Night Mode)
       ───────────────────────────────────────────────────────────────────── */

    const applyTheme = (theme) => {
        document.documentElement.setAttribute('data-theme', theme);
        dom.nightSwitch.setAttribute('aria-checked', String(theme === 'night'));
        localStorage.setItem('messger-theme', theme);
    };
    dom.nightSwitch.addEventListener('click', () => {
        const next = document.documentElement.getAttribute('data-theme') === 'night' ? 'day' : 'night';
        applyTheme(next);
        apiJSON('/api/settings/me/', { method: 'PATCH', body: JSON.stringify({ theme: next }) }).catch(() => {});
        toast(next === 'night' ? 'Tungi rejim YOQ' : 'Tungi rejim O\'CH');
    });
    applyTheme(localStorage.getItem('messger-theme') || 'night');
    if (localStorage.getItem('messger-drawer') === 'collapsed') dom.drawer.classList.add('is-collapsed');

    /* ─────────────────────────────────────────────────────────────────────
       14. SEARCH + KEYS + BANNER
       ───────────────────────────────────────────────────────────────────── */

    let listSearchTimer;
    dom.searchInput.addEventListener('input', () => {
        clearTimeout(listSearchTimer);
        dom.searchClear.hidden = !dom.searchInput.value;
        listSearchTimer = setTimeout(async () => {
            state.query = dom.searchInput.value;
            await loadChats();
            if (state.query.trim()) dom.app.classList.remove('is-list-hidden');
        }, 250);
    });
    dom.searchClear.addEventListener('click', () => {
        dom.searchInput.value = '';
        dom.searchClear.hidden = true;
        state.query = '';
        loadChats();
        dom.searchInput.focus();
    });

    dom.btnBack.addEventListener('click', () => dom.app.classList.remove('is-list-hidden'));
    dom.btnConvBack.addEventListener('click', () => dom.app.classList.remove('is-list-hidden'));

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (!dom.emojiPop.hidden) { dom.emojiPop.hidden = true; return; }
            if (isDrawerOpen()) return setDrawer(false);
            if (!dom.addModal.hidden) return dom.addModal.hidden = true;
        }
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            dom.app.classList.remove('is-list-hidden');
            dom.searchInput.focus();
            dom.searchInput.select();
        }
    });

    async function loadEvents() {
        const now = new Date();
        try {
            const data = await apiJSON(`/api/events/?month=${now.getMonth() + 1}&day=${now.getDate()}`);
            const items = data.results || (Array.isArray(data) ? data : []);
            const ev = items[0];
            if (ev) {
                dom.bannerBirthday.querySelector('.banner__text').innerHTML = `Bugun <b>${escapeHTML(ev.person_name)}</b> tug'ilgan kuni! ${ev.emoji || '🎂'}`;
                dom.bannerBirthday.hidden = false;
            } else {
                dom.bannerBirthday.hidden = true;
            }
        } catch { dom.bannerBirthday.hidden = true; }
    }
    dom.bannerBirthday.addEventListener('click', (e) => {
        if (e.target.closest('.banner__close')) dom.bannerBirthday.hidden = true;
    });

    /* ─────────────────────────────────────────────────────────────────────
       15. BOOT
       ───────────────────────────────────────────────────────────────────── */

    dom.addModeBtns.forEach(b => b.addEventListener('click', () => openAddChat(b.dataset.mode)));
    dom.modalClose.forEach(b => b.addEventListener('click', () => {
        $(b.dataset.close).hidden = true;
    }));
    [dom.addModal, dom.contactsModal].forEach(m => m.addEventListener('click', (e) => {
        if (e.target === m) m.hidden = true;
    }));
    dom.btnAddChat.addEventListener('click', () => openAddChat('private'));

    async function boot() {
        try {
            state.me = await apiJSON('/api/users/me/');
            localStorage.setItem('user', JSON.stringify(state.me));
        } catch { /* eski localStorage.profile yetarli */ }
        renderProfile();
        loadAccounts();
        loadEvents();
        try {
            const folders = await apiJSON('/api/folders/');
            state.folders = folders.results || (Array.isArray(folders) ? folders : []);
        } catch { state.folders = []; }
        renderRail();
        await loadChats();
        openGlobalSocket();
    }

    boot();
});