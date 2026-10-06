import tempfile

from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.models import Attachment, Chat, ChatMember, Message, Reaction

User = get_user_model()

PASSWORD = 'Katta-Parol-2026!'

# Testlar haqiqiy media papkasini ifloslantirmasligi uchun.
TEST_MEDIA = tempfile.mkdtemp(prefix='messger-test-media-')


class ChatTestMixin:
    def make_user(self, username, email=None):
        return User.objects.create_user(
            username=username,
            email=email or f'{username}@mail.com',
            password=PASSWORD,
        )

    def make_private_chat(self, a, b):
        chat = Chat.objects.create(type=Chat.Type.PRIVATE, created_by=a)
        ChatMember.objects.create(chat=chat, user=a, role=ChatMember.Role.ADMIN)
        ChatMember.objects.create(chat=chat, user=b)
        return chat


class ChatListTests(ChatTestMixin, APITestCase):
    def setUp(self):
        self.ali = self.make_user('ali')
        self.sardor = self.make_user('sardor')
        self.bek = self.make_user('bek')
        self.chat = self.make_private_chat(self.ali, self.sardor)

    def test_requires_auth(self):
        self.assertEqual(
            self.client.get('/api/chats/').status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_only_own_chats_are_listed(self):
        self.client.force_authenticate(self.ali)
        response = self.client.get('/api/chats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([c['id'] for c in response.data['results']], [self.chat.id])

    def test_chat_title_falls_back_to_other_member(self):
        self.client.force_authenticate(self.ali)
        response = self.client.get(f'/api/chats/{self.chat.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'sardor')

    def test_unread_count_is_per_user(self):
        Message.objects.create(
            chat=self.chat, sender=self.sardor, content='Salom', is_read=False
        )
        self.client.force_authenticate(self.ali)
        response = self.client.get('/api/chats/')
        self.assertEqual(response.data['results'][0]['unread_count'], 1)

        self.client.force_authenticate(self.sardor)
        response = self.client.get('/api/chats/')
        self.assertEqual(response.data['results'][0]['unread_count'], 0)

    def test_non_member_cannot_read_chat(self):
        self.client.force_authenticate(self.bek)
        response = self.client.get(f'/api/chats/{self.chat.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_member_cannot_list_chat_messages(self):
        self.client.force_authenticate(self.bek)
        response = self.client.get(f'/api/chats/{self.chat.id}/messages/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ChatCreateTests(ChatTestMixin, APITestCase):
    def setUp(self):
        self.ali = self.make_user('ali')
        self.sardor = self.make_user('sardor')
        self.client.force_authenticate(self.ali)

    def test_create_private_chat_adds_both_members(self):
        response = self.client.post(
            '/api/chats/',
            {'type': 'private', 'member_ids': [self.sardor.id]},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        chat = Chat.objects.get(pk=response.data['id'])
        self.assertEqual(
            set(chat.members.values_list('id', flat=True)),
            {self.ali.id, self.sardor.id},
        )
        member = ChatMember.objects.get(chat=chat, user=self.ali)
        self.assertEqual(member.role, ChatMember.Role.ADMIN)

    def test_duplicate_private_chat_is_rejected(self):
        self.client.post(
            '/api/chats/',
            {'type': 'private', 'member_ids': [self.sardor.id]},
            format='json',
        )
        response = self.client.post(
            '/api/chats/',
            {'type': 'private', 'member_ids': [self.sardor.id]},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_group_chat_requires_name(self):
        response = self.client.post(
            '/api/chats/',
            {'type': 'group', 'member_ids': [self.sardor.id]},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)

    def test_create_group_chat(self):
        response = self.client.post(
            '/api/chats/',
            {
                'type': 'group',
                'name': 'Frontend Jamoasi',
                'member_ids': [self.sardor.id],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Frontend Jamoasi')
        self.assertEqual(len(response.data['members']), 2)

    def test_create_chat_with_unknown_user(self):
        response = self.client.post(
            '/api/chats/',
            {'type': 'group', 'name': 'X', 'member_ids': [999999]},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MessageTests(ChatTestMixin, APITestCase):
    def setUp(self):
        self.ali = self.make_user('ali')
        self.sardor = self.make_user('sardor')
        self.bek = self.make_user('bek')
        self.chat = self.make_private_chat(self.ali, self.sardor)
        self.client.force_authenticate(self.ali)

    def test_send_message(self):
        response = self.client.post(
            f'/api/chats/{self.chat.id}/messages/',
            {'content': 'Salom!'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'Salom!')
        self.assertEqual(response.data['sender']['username'], 'ali')

    def test_empty_message_is_rejected(self):
        response = self.client.post(
            f'/api/chats/{self.chat.id}/messages/',
            {'content': '   '},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reply_to_must_be_in_same_chat(self):
        other = Chat.objects.create(type=Chat.Type.GROUP, name='Boshqa', created_by=self.ali)
        ChatMember.objects.create(chat=other, user=self.ali)
        foreign = Message.objects.create(chat=other, sender=self.ali, content='Boshqa chat')

        response = self.client.post(
            f'/api/chats/{self.chat.id}/messages/',
            {'content': 'Javob', 'reply_to': foreign.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('reply_to', response.data)

    def test_reply_includes_original(self):
        original = Message.objects.create(
            chat=self.chat, sender=self.sardor, content='Birinchi'
        )
        response = self.client.post(
            f'/api/chats/{self.chat.id}/messages/',
            {'content': 'Javob', 'reply_to': original.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['reply_to'], original.id)
        self.assertEqual(response.data['reply_to_detail']['id'], original.id)
        self.assertEqual(response.data['reply_to_detail']['content'], 'Birinchi')

    def test_messages_are_paginated_and_ordered(self):
        for i in range(5):
            Message.objects.create(
                chat=self.chat, sender=self.sardor, content=f'{i}'
            )
        response = self.client.get(
            f'/api/chats/{self.chat.id}/messages/', {'limit': 2}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 5)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['content'], '0')

    def test_search_messages(self):
        Message.objects.create(chat=self.chat, sender=self.sardor, content='frontend')
        Message.objects.create(chat=self.chat, sender=self.sardor, content='backend')
        response = self.client.get(
            f'/api/chats/{self.chat.id}/messages/', {'search': 'front'}
        )
        self.assertEqual(len(response.data['results']), 1)

    def test_edit_own_message(self):
        message = Message.objects.create(
            chat=self.chat, sender=self.ali, content='Eski'
        )
        response = self.client.patch(
            f'/api/messages/{message.id}/', {'content': 'Yangi'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content'], 'Yangi')
        self.assertTrue(response.data['is_edited'])

    def test_cannot_edit_other_members_message(self):
        message = Message.objects.create(
            chat=self.chat, sender=self.sardor, content='Sardorning'
        )
        response = self.client.patch(
            f'/api/messages/{message.id}/', {'content': 'O\'girtirdim'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        message.refresh_from_db()
        self.assertEqual(message.content, 'Sardorning')

    def test_group_admin_can_edit_any_message(self):
        group = Chat.objects.create(type=Chat.Type.GROUP, name='Guruh', created_by=self.sardor)
        ChatMember.objects.create(
            chat=group, user=self.sardor, role=ChatMember.Role.ADMIN
        )
        ChatMember.objects.create(chat=group, user=self.ali)
        message = Message.objects.create(chat=group, sender=self.ali, content='Mening')

        self.client.force_authenticate(self.sardor)
        response = self.client.patch(
            f'/api/messages/{message.id}/', {'content': 'Moderatsiya'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_is_soft(self):
        message = Message.objects.create(
            chat=self.chat, sender=self.ali, content='O\'chiriladi'
        )
        response = self.client.delete(f'/api/messages/{message.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        message.refresh_from_db()
        self.assertTrue(message.is_deleted)
        self.assertEqual(message.content, '')

    def test_non_member_cannot_send_message(self):
        self.client.force_authenticate(self.bek)
        response = self.client.post(
            f'/api/chats/{self.chat.id}/messages/',
            {'content': 'Begona'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_marks_chat_read(self):
        Message.objects.create(
            chat=self.chat, sender=self.sardor, content='1', is_read=False
        )
        Message.objects.create(
            chat=self.chat, sender=self.sardor, content='2', is_read=False
        )
        response = self.client.post(
            f'/api/chats/{self.chat.id}/read/', {}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['marked_read'], 2)
        self.assertEqual(
            Message.objects.filter(chat=self.chat, is_read=False).count(), 0
        )

    def test_message_read_action(self):
        message = Message.objects.create(
            chat=self.chat, sender=self.sardor, content='O\'qi'
        )
        response = self.client.post(f'/api/messages/{message.id}/read/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_read'])

    def test_reaction_toggles(self):
        message = Message.objects.create(chat=self.chat, sender=self.sardor, content='!')
        response = self.client.post(
            f'/api/messages/{message.id}/react/', {'kind': 'like'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['created'])
        self.assertEqual(Reaction.objects.count(), 1)

        response = self.client.post(
            f'/api/messages/{message.id}/react/', {'kind': 'like'}, format='json'
        )
        self.assertEqual(Reaction.objects.count(), 0)

    def test_reaction_rejects_bad_kind(self):
        message = Message.objects.create(chat=self.chat, sender=self.sardor, content='!')
        response = self.client.post(
            f'/api/messages/{message.id}/react/', {'kind': 'nope'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ChatMemberTests(ChatTestMixin, APITestCase):
    def setUp(self):
        self.ali = self.make_user('ali')
        self.sardor = self.make_user('sardor')
        self.bek = self.make_user('bek')
        self.group = Chat.objects.create(type=Chat.Type.GROUP, name='Guruh', created_by=self.ali)
        ChatMember.objects.create(
            chat=self.group, user=self.ali, role=ChatMember.Role.ADMIN
        )
        self.client.force_authenticate(self.ali)

    def test_list_members(self):
        response = self.client.get(f'/api/chats/{self.group.id}/members/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['user']['username'], 'ali')

    def test_add_member(self):
        response = self.client.post(
            f'/api/chats/{self.group.id}/members/',
            {'user_ids': [self.bek.id]},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ChatMember.objects.filter(chat=self.group, user=self.bek).exists())

    def test_remove_member(self):
        ChatMember.objects.create(chat=self.group, user=self.bek)
        response = self.client.delete(
            f'/api/chats/{self.group.id}/members/{self.bek.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ChatMember.objects.filter(chat=self.group, user=self.bek).exists())

    def test_cannot_remove_self(self):
        response = self.client.delete(
            f'/api/chats/{self.group.id}/members/{self.ali.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_admin_can_rename_chat(self):
        ChatMember.objects.create(chat=self.group, user=self.bek)
        self.client.force_authenticate(self.bek)
        response = self.client.patch(
            f'/api/chats/{self.group.id}/', {'name': 'Yangi nom'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_rename_chat(self):
        response = self.client.patch(
            f'/api/chats/{self.group.id}/', {'name': 'Yangi nom'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Yangi nom')


FAKE_AUDIO = b'\x1a\x45\xdf\xa3' + b'\x00' * 64  # webm (EBML) boshi


@override_settings(MEDIA_ROOT=TEST_MEDIA)
class VoiceUploadTests(ChatTestMixin, APITestCase):
    """REST upload yo'li (WS yopiq bo'lgandagi zaxira) va media serve qilinishi."""

    def setUp(self):
        self.ali = self.make_user('ali')
        self.client.force_authenticate(self.ali)

    def test_upload_voice_returns_usable_url(self):
        file = SimpleUploadedFile('voice.webm', FAKE_AUDIO, content_type='audio/webm')
        response = self.client.post(
            '/api/uploads/', {'file': file, 'kind': 'voice'}, format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['kind'], 'voice')
        self.assertTrue(response.data['url'])
        # URL media routeri orqali haqiqatan ham ochilishi kerak.
        path = response.data['url'].replace('http://testserver', '')
        self.assertTrue(path.startswith('/media/'), path)
        served = self.client.get(path)
        self.assertEqual(served.status_code, status.HTTP_200_OK)
        self.assertEqual(b''.join(served.streaming_content), FAKE_AUDIO)

    def test_attachment_is_persisted_with_meta(self):
        file = SimpleUploadedFile('voice.webm', FAKE_AUDIO, content_type='audio/webm')
        response = self.client.post(
            '/api/uploads/', {'file': file, 'kind': 'voice'}, format='multipart'
        )
        att = Attachment.objects.get(pk=response.data['id'])
        self.assertEqual(att.kind, Attachment.Kind.VOICE)
        self.assertEqual(att.size, len(FAKE_AUDIO))
        self.assertEqual(att.mime_type, 'audio/webm')


class VoiceMessageWebSocketTests(ChatTestMixin, TransactionTestCase):
    """Ovozli xabar WebSocket binary kadr orqali yuboriladi va guruhga qaytariladi."""

    def setUp(self):
        self.ali = self.make_user('ali')
        self.sardor = self.make_user('sardor')
        self.chat = self.make_private_chat(self.ali, self.sardor)

    def communicator(self, user, chat_id):
        from channels.routing import URLRouter
        from rest_framework_simplejwt.tokens import AccessToken

        from chats.routing import websocket_urlpatterns

        token = str(AccessToken.for_user(user))
        return WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            f'/ws/chat/{chat_id}/?token={token}',
        )

    def global_communicator(self, user):
        from channels.routing import URLRouter
        from rest_framework_simplejwt.tokens import AccessToken

        from chats.routing import websocket_urlpatterns

        token = str(AccessToken.for_user(user))
        return WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            f'/ws/global/?token={token}',
        )

    async def test_voice_round_trip(self):
        sender = self.communicator(self.ali, self.chat.id)
        receiver = self.communicator(self.sardor, self.chat.id)
        listener = self.global_communicator(self.sardor)
        for comm in (sender, receiver, listener):
            self.assertTrue((await comm.connect())[0])
            self.assertEqual((await comm.receive_json_from(timeout=5))['type'], 'connected')

        await sender.send_json_to({
            'action': 'voice.begin',
            'client_id': 'cid-voice-1',
            'mime': 'audio/webm',
            'duration': 7,
            'reply_to': None,
        })
        ready = await sender.receive_json_from(timeout=5)
        self.assertEqual(ready['type'], 'voice.ready')

        await sender.send_to(bytes_data=FAKE_AUDIO)
        broadcast = await sender.receive_json_from(timeout=5)
        self.assertEqual(broadcast['type'], 'message.new')

        data = broadcast['data']
        self.assertEqual(data['client_id'], 'cid-voice-1')
        self.assertEqual(data['attachment'], data['attachment_detail']['id'])
        self.assertEqual(data['attachment_detail']['kind'], 'voice')
        self.assertTrue(data['attachment_detail']['url'].startswith('/media/'))
        self.assertEqual(data['attachment_detail']['duration'], 7)

        # Chat guruhi orqali qabul qiluvchiga ham xabar yetadi.
        got = await receiver.receive_json_from(timeout=5)
        self.assertEqual(got['type'], 'message.new')
        self.assertEqual(got['data']['client_id'], 'cid-voice-1')

        # Global notification — chat yopiq bo'lsa ham alohida kanal keladi.
        note = await listener.receive_json_from(timeout=5)
        self.assertEqual(note['type'], 'notification')
        self.assertEqual(note['data']['event'], 'message.new')
        self.assertEqual(note['data']['message']['client_id'], 'cid-voice-1')

        self.assertEqual(await self.count_async(), 1)

        await sender.disconnect()
        await receiver.disconnect()
        await listener.disconnect()

    async def count_async(self):
        from channels.db import database_sync_to_async

        @database_sync_to_async
        def _count():
            return Message.objects.filter(chat_id=self.chat.id).count()

        return await _count()

    async def test_voice_without_begin_is_rejected(self):
        sender = self.communicator(self.ali, self.chat.id)
        self.assertTrue((await sender.connect())[0])
        self.assertEqual((await sender.receive_json_from(timeout=5))['type'], 'connected')
        await sender.send_to(bytes_data=FAKE_AUDIO)
        err = await sender.receive_json_from(timeout=5)
        self.assertEqual(err['type'], 'error')
        self.assertEqual(err['code'], 'voice')
        await sender.disconnect()

    async def test_oversized_voice_is_rejected(self):
        from chats import consumers

        sender = self.communicator(self.ali, self.chat.id)
        self.assertTrue((await sender.connect())[0])
        self.assertEqual((await sender.receive_json_from(timeout=5))['type'], 'connected')
        await sender.send_json_to({'action': 'voice.begin', 'client_id': 'big'})
        self.assertEqual((await sender.receive_json_from(timeout=5))['type'], 'voice.ready')
        await sender.send_to(bytes_data=b'x' * (consumers.VOICE_MAX_BYTES + 1))
        err = await sender.receive_json_from(timeout=10)
        self.assertEqual(err['type'], 'error')
        self.assertEqual(err['code'], 'voice')
        await sender.disconnect()
