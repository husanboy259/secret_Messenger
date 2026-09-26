import datetime

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Event

User = get_user_model()

STRONG_PASSWORD = 'Katta-Parol-2026!'


class AuthTests(APITestCase):
    def test_register_returns_tokens_and_user(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'ali',
                'email': 'Ali@Mail.com',
                'password': STRONG_PASSWORD,
                'password_confirm': STRONG_PASSWORD,
                'display_name': 'Ali',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['username'], 'ali')
        self.assertEqual(response.data['user']['email'], 'ali@mail.com')

        user = User.objects.get(username='ali')
        self.assertTrue(user.check_password(STRONG_PASSWORD))
        self.assertNotEqual(user.password, STRONG_PASSWORD)

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(
            username='ali', email='ali@mail.com', password=STRONG_PASSWORD
        )
        response = self.client.post(
            reverse('register'),
            {
                'username': 'ali2',
                'email': 'ALI@mail.com',
                'password': STRONG_PASSWORD,
                'password_confirm': STRONG_PASSWORD,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_register_rejects_mismatched_passwords(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'ali',
                'email': 'ali@mail.com',
                'password': STRONG_PASSWORD,
                'password_confirm': 'Boshqa-Parol-1!',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_confirm', response.data)

    def test_login_with_username(self):
        User.objects.create_user(
            username='ali', email='ali@mail.com', password=STRONG_PASSWORD
        )
        response = self.client.post(
            reverse('login'),
            {'username': 'ali', 'password': STRONG_PASSWORD},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['username'], 'ali')

    def test_login_with_email(self):
        User.objects.create_user(
            username='ali', email='ali@mail.com', password=STRONG_PASSWORD
        )
        response = self.client.post(
            reverse('login'),
            {'username': 'ali@mail.com', 'password': STRONG_PASSWORD},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], 'ali')

    def test_login_wrong_password(self):
        User.objects.create_user(
            username='ali', email='ali@mail.com', password=STRONG_PASSWORD
        )
        response = self.client.post(
            reverse('login'), {'username': 'ali', 'password': 'noto-gri'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_unknown_user(self):
        response = self.client.post(
            reverse('login'), {'username': 'yoq', 'password': STRONG_PASSWORD}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_me_requires_auth(self):
        self.assertEqual(
            self.client.get(reverse('me')).status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_me_get_and_patch(self):
        user = User.objects.create_user(
            username='ali', email='ali@mail.com', password=STRONG_PASSWORD
        )
        self.client.force_authenticate(user)

        response = self.client.get(reverse('me'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'ali')

        response = self.client.patch(
            reverse('me'), {'bio': 'Dasturchi'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.bio, 'Dasturchi')

    def test_me_cannot_change_username(self):
        user = User.objects.create_user(
            username='ali', email='ali@mail.com', password=STRONG_PASSWORD
        )
        self.client.force_authenticate(user)
        self.client.patch(reverse('me'), {'username': 'haker'}, format='json')
        user.refresh_from_db()
        self.assertEqual(user.username, 'ali')

    def test_logout_blacklists_refresh_token(self):
        from rest_framework_simplejwt.tokens import RefreshToken

        user = User.objects.create_user(
            username='ali', email='ali@mail.com', password=STRONG_PASSWORD
        )
        self.client.force_authenticate(user)
        refresh = str(RefreshToken.for_user(user))

        response = self.client.post(reverse('logout'), {'refresh': refresh}, format='json')
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

        response = self.client.post(
            reverse('token_refresh'), {'refresh': refresh}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_refresh(self):
        user = User.objects.create_user(
            username='ali', email='ali@mail.com', password=STRONG_PASSWORD
        )
        self.client.force_authenticate(user)
        response = self.client.post(reverse('logout'), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_list_requires_auth_and_filters(self):
        User.objects.create_user(username='ali', password=STRONG_PASSWORD)
        User.objects.create_user(
            username='sardor', email='sardor@mail.com', password=STRONG_PASSWORD
        )
        self.assertEqual(
            self.client.get(reverse('user_list')).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.client.force_authenticate(User.objects.get(username='ali'))
        response = self.client.get(reverse('user_list'), {'search': 'sardor'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([u['username'] for u in response.data], ['sardor'])


class EventViewSetTests(APITestCase):
    """Tug'ilgan kun banner'i.

    Eslatma: xom `EXTRACT(MONTH FROM date)` SQL'i SQLite'da
    `OperationalError` beradi - `ExtractMonth`/`ExtractDay` ishlatiladi.
    """

    def setUp(self):
        self.ali = User.objects.create_user(
            username='ali', email='ali@mail.com', password=STRONG_PASSWORD
        )
        self.sardor = User.objects.create_user(
            username='sardor', email='sardor@mail.com', password=STRONG_PASSWORD
        )
        self.client.force_authenticate(self.ali)
        self.url = reverse('event-list')
        self.today = timezone.now().date()

    def _event(self, owner, person_name, date):
        return Event.objects.create(
            owner=owner,
            kind=Event.Kind.BIRTHDAY,
            person_name=person_name,
            date=date,
        )

    def test_list_requires_auth(self):
        self.client.force_authenticate(None)
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_month_day_filter_matches_across_years(self):
        self._event(
            self.ali, 'Bir yil keyin', self.today + datetime.timedelta(days=365)
        )
        self._event(self.ali, 'Boshqa oy', self.today.replace(month=1, day=1))

        response = self.client.get(
            self.url, {'month': self.today.month, 'day': self.today.day}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [e['person_name'] for e in response.data['results']]
        self.assertEqual(names, ['Bir yil keyin'])

    def test_filter_is_scoped_to_owner(self):
        self._event(self.sardor, 'Sardorning tugilgan kuni', self.today)

        response = self.client.get(
            self.url, {'month': self.today.month, 'day': self.today.day}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_invalid_params_do_not_crash(self):
        for params in ({'month': 'abc', 'day': 'xyz'}, {'month': 13, 'day': 40}, {}):
            with self.subTest(params=params):
                response = self.client.get(self.url, params)
                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_ordered_by_date(self):
        self._event(self.ali, 'Kechagi', self.today - datetime.timedelta(days=1))
        self._event(self.ali, 'Ertagi', self.today + datetime.timedelta(days=1))

        response = self.client.get(self.url)

        self.assertEqual(
            [e['person_name'] for e in response.data['results']],
            ['Kechagi', 'Ertagi'],
        )

