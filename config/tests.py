"""Frontend sahifalarini berish (faqat DEBUG rejimida)."""

from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(DEBUG=True)
class DevPageTests(TestCase):
    def body(self, url):
        """`dev_file` FileResponse qaytaradi — streaming'dan o'qish kerak."""
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return b''.join(response.streaming_content).decode('utf-8')

    def test_pages_are_served(self):
        for name in ('home', 'login_page', 'register_page', 'messenger'):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)

    def test_root_serves_index_html(self):
        response = self.client.get(reverse('home'))
        self.assertIn('text/html', response['Content-Type'])
        self.assertIn('Messger', self.body(reverse('home')))

    def test_register_page_contains_form_fields(self):
        body = self.body(reverse('register_page'))
        for field in ('username', 'email', 'password', 'password_confirm'):
            with self.subTest(field=field):
                self.assertIn(f'id="{field}"', body)
        self.assertIn('/api/auth/register/', body)

    def test_static_assets_are_served(self):
        for url in ('/styles.css', '/app.js', '/messenger.css', '/messenger.js'):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_messenger_page_has_app_shell(self):
        body = self.body(reverse('messenger'))
        for marker in (
            'class="rail"',
            'class="panel"',
            'class="stage"',
            'class="drawer"',
            'messenger.css',
            'messenger.js',
            'Select a chat to start messaging',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, body)

    def test_arbitrary_files_are_not_served(self):
        for url in (
            '/db.sqlite3',
            '/manage.py',
            '/config/settings.py',
            '/accounts/views.py',
            '/.git/config',
            '/ROADMAP_BACKEND.md',
            '/../db.sqlite3',
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)


class DevPageDisabledTests(TestCase):
    """DEBUG=False da sahifalar berilmasligi kerak."""

    def test_pages_are_404_when_debug_off(self):
        with self.settings(DEBUG=False):
            for name in ('home', 'login_page', 'register_page', 'messenger'):
                with self.subTest(name=name):
                    self.assertEqual(self.client.get(reverse(name)).status_code, 404)
