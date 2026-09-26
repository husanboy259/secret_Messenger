"""
WebSocket smoke test — ikki foydalanuvchi, bitta chat.

    python manage.py runserver
    python ws_smoke_test.py
"""

import asyncio
import json
import os
import sys

import django
import requests
import websockets

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

API = 'http://127.0.0.1:8000'
WS = 'ws://127.0.0.1:8000'
PASSWORD = 'Katta-Parol-2026!'

ok = fail = 0


def check(label, condition, extra=''):
    global ok, fail
    if condition:
        ok += 1
        print(f'  PASS  {label}')
    else:
        fail += 1
        print(f'  FAIL  {label} {extra}')


def register_or_login(username):
    payload = {
        'username': username,
        'email': f'{username}@mail.uz',
        'password': PASSWORD,
        'password_confirm': PASSWORD,
        'display_name': username.title(),
    }
    response = requests.post(f'{API}/api/auth/register/', json=payload, timeout=10)
    if response.status_code == 201:
        return response.json()
    response = requests.post(
        f'{API}/api/auth/login/',
        json={'username': username, 'password': PASSWORD},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


async def main():
    print('1. Login')
    ali = register_or_login('ws_ali')
    sardor = register_or_login('ws_sardor')
    gabriel = register_or_login('ws_gabriel')
    ali_h = {'Authorization': f"Bearer {ali['access']}"}
    check('ali login', bool(ali['access']), ali)
    check('account_id qaytdi', 'account_id' in ali, ali)
    check('emoji_status bor', 'emoji_status' in ali['user'], ali['user'])

    print('2. Private chat yaratish')
    users = requests.get(f'{API}/api/users/?search=ws_sardor', headers=ali_h, timeout=10).json()
    peer = next(u for u in users if u['username'] == 'ws_sardor')
    response = requests.post(
        f'{API}/api/chats/',
        headers=ali_h,
        json={'type': 'private', 'member_ids': [peer['id']]},
        timeout=10,
    )
    if response.status_code == 201:
        check('chat yaratildi', True)
        chat_id = response.json()['id']
    elif 'allaqachon mavjud' in response.text:
        check('chat yaratildi (allaqachon bor)', True)
        chats = requests.get(f'{API}/api/chats/', headers=ali_h, timeout=10).json()
        chat_id = next(
            c['id'] for c in chats['results']
            if c['type'] == 'private' and 'ws_sardor' in c['title'].lower()
        )
    else:
        check('chat yaratildi', False, response.text)
        sys.exit(1)
    print(f'      chat_id = {chat_id}')

    print('3. Token yaroqsiz — 4401 kutilmoqda')
    try:
        async with websockets.connect(f'{WS}/ws/chat/{chat_id}/?token=yoq') as sock:
            first = json.loads(await asyncio.wait_for(sock.recv(), timeout=5))
            code = first.get('code')
            check('4401 yuborildi', code == 4401, first)
    except Exception as exc:
        check('4401 yuborildi', False, repr(exc))

    print('4. A\'zo bo\'lmagan user — 4403 kutilmoqda')
    try:
        async with websockets.connect(
            f'{WS}/ws/chat/{chat_id}/?token={gabriel["access"]}'
        ) as sock:
            first = json.loads(await asyncio.wait_for(sock.recv(), timeout=5))
            check('4403 yuborildi', first.get('code') == 4403, first)
    except Exception as exc:
        check('4403 yuborildi', False, repr(exc))

    print('5. Haqiqiy xabar yuborish (broadcast)')
    async with websockets.connect(f'{WS}/ws/chat/{chat_id}/?token={ali["access"]}') as sock:
        hello = json.loads(await asyncio.wait_for(sock.recv(), timeout=5))
        check('connected', hello.get('type') == 'connected', hello)

        await sock.send(json.dumps({
            'action': 'message.create',
            'text': 'Salom, WebSocket!',
            'client_id': 'smoke-1',
        }))
        sent = json.loads(await asyncio.wait_for(sock.recv(), timeout=5))
        check('message.new qaytdi', sent.get('type') == 'message.new', sent)
        data = sent.get('data', {})
        check('content to\'g\'ri', data.get('content') == 'Salom, WebSocket!', data)
        check('client_id saqlangan', data.get('client_id') == 'smoke-1', data)
        message_id = data.get('id')
        print(f'      message_id = {message_id}')

        print('6. Dedup — bir xil client_id yuborilsa qaytmaydi')
        await sock.send(json.dumps({
            'action': 'message.create',
            'text': 'Salom, WebSocket!',
            'client_id': 'smoke-1',
        }))
        again = json.loads(await asyncio.wait_for(sock.recv(), timeout=5))
        check('bir xil id qaytarildi', again['data']['id'] == message_id, again['data'])

        print('7. Typing indicator')
        await sock.send(json.dumps({'action': 'typing', 'is_typing': True}))
        typing = json.loads(await asyncio.wait_for(sock.recv(), timeout=5))
        check('typing event', typing.get('type') == 'typing', typing)
        check('is_typing=True', typing['data']['is_typing'] is True, typing['data'])

        print('8. Bo\'sh xabar rad etilishi')
        await sock.send(json.dumps({'action': 'message.create', 'text': '   '}))
        error = json.loads(await asyncio.wait_for(sock.recv(), timeout=5))
        check('invalid rad etildi', error.get('type') == 'error', error)

    print('9. REST orqali tekshirish (DB ga yozilganmi)')
    messages = requests.get(
        f'{API}/api/chats/{chat_id}/messages/',
        headers=ali_h,
        params={'search': 'WebSocket'},
        timeout=10,
    ).json()
    check('xabar DB da bor', messages['count'] >= 1, messages)
    if messages['count']:
        row = messages['results'][0]
        check('id mos keldi', row['id'] == message_id, row)
        check('sender ali', row['sender']['username'] == 'ws_ali', row['sender'])

    print('10. Global socket')
    async with websockets.connect(f'{WS}/ws/global/?token={ali["access"]}') as sock:
        hello = json.loads(await asyncio.wait_for(sock.recv(), timeout=5))
        check('global connected', hello.get('type') == 'connected', hello)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)

    print()
    print(f'  {ok} passed, {fail} failed')
    sys.exit(1 if fail else 0)
