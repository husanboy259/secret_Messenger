"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.
For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Django ilovasi AVVAL yuklanishi kerak — undan keyin modellar import qilinadi.
django_asgi_app = get_asgi_application()

from chats.routing import websocket_urlpatterns  # noqa: E402  (import pastda shart)

application = ProtocolTypeRouter(
    {
        'http': django_asgi_app,
        'websocket': AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
