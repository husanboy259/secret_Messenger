import mimetypes

from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, Http404
from django.urls import include, path, re_path
from django.views.static import serve
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.views import (
    AccountViewSet,
    ContactViewSet,
    EventViewSet,
    MeView,
    UserListView,
    UserSettingsView,
)
from chats.views import CallViewSet, ChatViewSet, FolderViewSet, MessageViewSet, UploadView

router = DefaultRouter()
router.register('chats', ChatViewSet, basename='chat')
router.register('messages', MessageViewSet, basename='message')
router.register('folders', FolderViewSet, basename='folder')
router.register('accounts', AccountViewSet, basename='account')
router.register('contacts', ContactViewSet, basename='contact')
router.register('events', EventViewSet, basename='event')
router.register('calls', CallViewSet, basename='call')

# Faqat shu fayllar brauzerga beriladi. Butun loyiha papkasini document_root
# qilib bermaslik kerak — aks holda db.sqlite3, config/settings.py (SECRET_KEY)
# va manage.py ham ochiq bo'lib qoladi.
DEV_PAGES = (
    'index.html',
    'login.html',
    'register.html',
    'profile.html',
    'styles.css',
    'app.js',
    'messenger.html',
    'messenger.css',
    'messenger.js',
    'config.js',
)


def dev_file(request, filename):
    """frontend/ papkasidagi frontend fayllarini beradi (faqat DEBUG=True da)."""
    if not settings.DEBUG or filename not in DEV_PAGES:
        raise Http404('Sahifa topilmadi.')

    target = settings.BASE_DIR / 'frontend' / filename
    if not target.is_file():
        raise Http404('Sahifa topilmadi.')

    content_type, _ = mimetypes.guess_type(filename)
    return FileResponse(target.open('rb'), content_type=content_type)


urlpatterns = [
    path('', dev_file, {'filename': 'index.html'}, name='home'),
    path('index.html', dev_file, {'filename': 'index.html'}),
    path('login.html', dev_file, {'filename': 'login.html'}, name='login_page'),
    path('register.html', dev_file, {'filename': 'register.html'}, name='register_page'),
    path('profile.html', dev_file, {'filename': 'profile.html'}, name='profile_page'),
    path('styles.css', dev_file, {'filename': 'styles.css'}),
    path('app.js', dev_file, {'filename': 'app.js'}),
    path('messenger.html', dev_file, {'filename': 'messenger.html'}, name='messenger'),
    path('messenger.css', dev_file, {'filename': 'messenger.css'}),
    path('messenger.js', dev_file, {'filename': 'messenger.js'}),
    path('config.js', dev_file, {'filename': 'config.js'}),

    path('admin/', admin.site.urls),

    # --- Fayl yuklash (rasm / video / ovoz) ---
    path('api/uploads/', UploadView.as_view(), name='upload'),

    # --- Auth ---
    path('api/', include('accounts.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/users/me/', MeView.as_view(), name='me'),
    path('api/users/', UserListView.as_view(), name='user_list'),
    path('api/settings/me/', UserSettingsView.as_view(), name='settings_me'),

    # --- Chats & Messages ---
    path('api/', include(router.urls)),
]

# Media fayllar (audio / rasm / video) production'da ham ochiq bo'lishi shart —
# aks holda ovozli xabarlar 404 bo'lib eshitilmaydi. document_root dynamic
# o'qiladi, shunda override_settings (testlar) ham ishlaydi.
def media_serve(request, path):
    return serve(request, path, document_root=settings.MEDIA_ROOT)


urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', media_serve, name='media'),
]
