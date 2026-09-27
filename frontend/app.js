    /* ==========================================================================
   MESSGER — INTERACTION SCRIPT (VANILLA JAVASCRIPT)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    
    // --- 1. DARK / LIGHT THEME TOGGLE ---
    const themeToggleBtn = document.getElementById('theme-toggle');
    const currentTheme = localStorage.getItem('theme') || 'dark';
    
    // Set initial theme
    if (currentTheme === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
    }
    
    themeToggleBtn.addEventListener('click', () => {
        let theme = document.documentElement.getAttribute('data-theme');
        if (theme === 'light') {
            document.documentElement.removeAttribute('data-theme');
            localStorage.setItem('theme', 'dark');
        } else { 
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
        }
    });

    // --- 2. MOBILE MENU TOGGLE ---
    const menuToggle = document.getElementById('menu-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            navLinks.style.display = navLinks.style.display === 'flex' ? 'none' : 'flex';
            menuToggle.classList.toggle('active');
        });
    }

    // --- 3. HERO MINI CHAT INTERACTION (SIMULATED WEBSOCKET) ---
    const mockupInput = document.getElementById('mockup-input');
    const mockupSendBtn = document.getElementById('mockup-send');
    const mockupMessages = document.getElementById('mockup-messages');

    // Bot responses
    const botReplies = [
        "Ajoyib! O'rganishda davom eting! 💻",
        "Loyiha juda tez rivojlanyapti! 🚀",
        "Real-time xabarlar WebSocket yordamida uzatilmoqda. ⚡",
        "Siz yozgan har qanday xabarga javob bera olaman! 😉",
        "Dizayn juda qulay va moslashuvchan, shunday emasmi? ✨"
    ];
    let replyIndex = 0;

    function sendMockupMessage() {
        const text = mockupInput.value.trim();
        if (!text) return;

        // Clear input
        mockupInput.value = '';

        // Create outgoing user message
        const outMsg = document.createElement('div');
        outMsg.className = 'chat-message outgoing';
        
        const now = new Date();
        const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
        
        outMsg.innerHTML = `
            <div class="message-content">
                <p>${escapeHTML(text)}</p>
                <span class="time">${timeStr}</span>
            </div>
        `;
        
        mockupMessages.appendChild(outMsg);
        scrollMockupToBottom();

        // Simulate reply with delay
        setTimeout(() => {
            showMockupTypingIndicator(() => {
                const inMsg = document.createElement('div');
                inMsg.className = 'chat-message incoming';
                
                const replyText = botReplies[replyIndex % botReplies.length];
                replyIndex++;

                inMsg.innerHTML = `
                    <div class="avatar">👨‍💻</div>
                    <div class="message-content">
                        <p>${replyText}</p>
                        <span class="time">${timeStr}</span>
                    </div>
                `;
                mockupMessages.appendChild(inMsg);
                scrollMockupToBottom();
            });
        }, 1000);
    }

    function showMockupTypingIndicator(callback) {
        // Create indicator element
        const indicator = document.createElement('div');
        indicator.className = 'chat-message incoming typing-indicator-msg';
        indicator.innerHTML = `
            <div class="avatar">👨‍💻</div>
            <div class="message-content" style="padding: 10px 14px;">
                <div class="typing-dots">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        mockupMessages.appendChild(indicator);
        scrollMockupToBottom();

        // Styling for dots if not in CSS
        const style = document.createElement('style');
        style.innerHTML = `
            .typing-dots { display: flex; gap: 4px; align-items: center; height: 16px; }
            .typing-dots span { width: 6px; height: 6px; background-color: var(--text-secondary); border-radius: 50%; animation: typing 1.4s infinite both; }
            .typing-dots span:nth-child(2) { animation-delay: .2s; }
            .typing-dots span:nth-child(3) { animation-delay: .4s; }
            @keyframes typing { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; } 40% { transform: scale(1); opacity: 1; } }
        `;
        document.head.appendChild(style);

        setTimeout(() => {
            indicator.remove();
            callback();
        }, 1200);
    }

    function scrollMockupToBottom() {
        mockupMessages.scrollTop = mockupMessages.scrollHeight;
    }

    if (mockupSendBtn) {
        mockupSendBtn.addEventListener('click', sendMockupMessage);
        mockupInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMockupMessage();
        });
    }


    // --- 4. DASHBOARD CHAT INTERACTION ---
    const demoChatInput = document.getElementById('demo-chat-input');
    const demoChatSend = document.getElementById('demo-chat-send');
    const chatAreaMessages = document.querySelector('.chat-area-messages');
    const dynamicDemoMsg = document.getElementById('dynamic-demo-msg');

    function sendDemoChatMessage() {
        const text = demoChatInput.value.trim();
        if (!text) return;

        demoChatInput.value = '';

        const now = new Date();
        const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

        // Append User Message
        const userBubble = document.createElement('div');
        userBubble.className = 'msg bubble-out';
        userBubble.innerHTML = `
            <p>${escapeHTML(text)}</p>
            <span class="msg-time">${timeStr}</span>
        `;
        chatAreaMessages.appendChild(userBubble);
        scrollDemoChatToBottom();

        // Trigger dynamic simulated team response after a short delay
        if (dynamicDemoMsg && dynamicDemoMsg.style.display === 'none') {
            setTimeout(() => {
                dynamicDemoMsg.style.display = 'flex';
                scrollDemoChatToBottom();
            }, 1200);
        }
    }

    function scrollDemoChatToBottom() {
        chatAreaMessages.scrollTop = chatAreaMessages.scrollHeight;
    }

    if (demoChatSend) {
        demoChatSend.addEventListener('click', sendDemoChatMessage);
        demoChatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendDemoChatMessage();
        });
    }

    // Helper: Escape HTML to prevent injection
    function escapeHTML(str) {
        return str.replace(/[&<>'"]/g, 
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag] || tag)
        );
    }
});
