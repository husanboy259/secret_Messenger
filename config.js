/* =====================================================================
   Deploy sozlamalari (Render backend + Vercel frontend)
   - API_BASE: backend REST / upload URL
       lokal (Django ichida):  ''  → barcha so'rovlar shu sahifa bilan bir xil hostga
       deploy:                 'https://messger-backend.onrender.com'
   - WS_BASE: WebSocket URL
       lokal:  ''  → location.host ga mos keladi (ws/wss avtomatik)
       deploy: 'wss://messger-backend.onrender.com'
   ===================================================================== */
window.MESSGER = {
    API_BASE: '',
    WS_BASE: ''
};