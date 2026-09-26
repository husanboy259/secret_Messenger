from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.models import Chat, ChatMember, Message, Reaction

User = get_user_model()

PASSWORD = 'Katta-Parol-2026!'


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
