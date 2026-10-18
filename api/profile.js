/* Vercel serverless function — server-rendered Open Graph (link preview)
 * for /open/<username>.
 *
 * vercel.json rewrite:  /open/:username  ->  /api/profile
 * (Vercel turns path params into query params, so req.query.username is set.)
 *
 * Telegram / WhatsApp / Instagram / Facebook kabi crawler'lar JS ishlatmaydi,
 * shuning uchun preview meta teglarni shu yerda server tomonida to'ldiramiz.
 * Foydalanuvchiga esa statik open.html qaytariladi (open.js keyin jonlantiradi).
 */

var API_BASE = process.env.MESSGER_API_BASE || 'https://secret-messenger-real.onrender.com';

function esc(s) {
    return String(s == null ? '' : s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function setMeta(html, id, content) {
    var re = new RegExp('(<meta[^>]*id="' + id + '"[^>]*content=")[^"]*(")', 'i');
    if (re.test(html)) return html.replace(re, '$1' + esc(content) + '$2');
    return html;
}

module.exports = async function handler(req, res) {
    var raw = (req.query && req.query.username) ? req.query.username : '';
    var username = String(raw).replace(/^@/, '').trim();
    var host = req.headers['x-forwarded-host'] || req.headers.host || 'messger-six.vercel.app';
    var proto = String(req.headers['x-forwarded-proto'] || 'https').split(',')[0].trim();

    var html = '';
    try {
        var pageRes = await fetch(proto + '://' + host + '/open.html');
        html = await pageRes.text();
    } catch (e) { html = ''; }

    if (!html || html.indexOf('<head') === -1) {
        html = '<!DOCTYPE html><html lang="uz"><head><meta charset="utf-8">' +
            '<meta name="viewport" content="width=device-width, initial-scale=1">' +
            '<title>Messger</title>' +
            '<meta property="og:title" content="Messger" id="ogTitle">' +
            '<meta property="og:description" content="Messger" id="ogDesc">' +
            '<meta property="og:url" content="" id="ogUrl">' +
            '<meta name="twitter:title" content="Messger" id="twTitle">' +
            '<meta name="twitter:description" content="Messger" id="twDesc">' +
            '<link rel="stylesheet" href="/open.css">' +
            '</head><body><div class="open-wrap"></div>' +
            '<script src="/config.js"></script><script src="/i18n.js"></script>' +
            '<script src="/open.js"></script></body></html>';
    }

    var pageUrl = proto + '://' + host + '/open/' + encodeURIComponent(username);
    var title = 'Messger';
    var desc = "Messger'da profilni ochish";
    var image = '';
    var ogType = 'profile';

    if (username) {
        try {
            var apiRes = await fetch(API_BASE + '/api/public/' + encodeURIComponent(username) + '/');
            if (apiRes.ok) {
                var d = await apiRes.json();
                var kind = d.type === 'channel' ? 'Kanal' : d.type === 'group' ? 'Guruh' : 'Foydalanuvchi';
                var handle = d.username || username;
                title = (d.display_name || handle) + ' — Messger';
                desc = (d.about && String(d.about).trim())
                    ? String(d.about).trim().slice(0, 180)
                    : (kind + ' · @' + handle + (d.members_count ? " · " + d.members_count + " a'zo" : ''));
                if (d.avatar) image = d.avatar.charAt(0) === '/' ? API_BASE + d.avatar : d.avatar;
                ogType = d.type === 'user' ? 'profile' : 'website';
            } else {
                title = 'Profil topilmadi — Messger';
                desc = "Bu havola o'chirilgan yoki noto'g'ri kiritilgan.";
            }
        } catch (e) { /* generic preview */ }
    }

    html = setMeta(html, 'ogTitle', title);
    html = setMeta(html, 'ogDesc', desc);
    html = setMeta(html, 'ogUrl', pageUrl);
    html = setMeta(html, 'twTitle', title);
    html = setMeta(html, 'twDesc', desc);
    html = html.replace('<title>Profil — Messger</title>', '<title>' + esc(title) + '</title>');
    html = html.replace('content="profile"', 'content="' + ogType + '"');

    if (image) {
        html = html.replace('content="summary"', 'content="summary_large_image"');
        html = html.replace('</head>',
            '<meta property="og:image" content="' + esc(image) + '">' +
            '<meta name="twitter:image" content="' + esc(image) + '">' +
            '<meta property="og:image:alt" content="' + esc(title) + '"></head>');
    }

    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.setHeader('Cache-Control', 'public, max-age=0, s-maxage=600, stale-while-revalidate=86400');
    res.status(200).send(html);
};
