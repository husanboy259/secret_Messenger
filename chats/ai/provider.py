"""LLM client — OpenAI-compatible API (Google AI Studio/Gemini, OpenRouter va boshqa).

Faqat stdlib `urllib` ishlatiladi, shuning uchun yangi pip-bog'liqlik kerak emas.
Konfiguratsiya `settings.py` dagi `AI_*` o'zgaruvchilardan olinadi.
"""

import json
import urllib.error
import urllib.request

from django.conf import settings


class LLMError(Exception):
    """Provayderga ulanish / javobda xatolik."""


def chat_completion(messages, *, model=None, max_tokens=None, temperature=0.7):
    """OpenAI-compatible `/chat/completions` chaqirish.

    `messages` — [{'role': 'system'|'user'|'assistant', 'content': str}].
    Javob matnini qaytaradi.
    """
    if not settings.AI_API_KEY:
        raise LLMError('AI_API_KEY sozlanmagan.')

    base = settings.AI_BASE_URL
    body = {
        'model': model or settings.AI_MODEL,
        'messages': messages,
        'max_tokens': max_tokens or settings.AI_MAX_TOKENS,
        'temperature': temperature,
    }
    # Autentifikatsiya. Gemini'ning OpenAI-moslik (compatibility) endpointi
    # `Authorization: Bearer <key>` kutadi; OpenRouter ham xuddi shunday. Gemini
    # uchun qo'shimcha `x-goog-api-key` ham yuboriladi (zararsiz, ikkalasini ham
    # qabul qiladi) — turli konfiguratsiyalarda ishlashi uchun.
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {settings.AI_API_KEY}',
        # OpenRouter raqamlarini ko'rsatish uchun (ixtiyoriy)
        'HTTP-Referer': 'https://secret-messenger-sepia-xi.vercel.app/',
        'X-Title': 'Messger Support',
    }
    if 'generativelanguage.googleapis.com' in base:
        headers['x-goog-api-key'] = settings.AI_API_KEY

    request = urllib.request.Request(
        f'{base}/chat/completions',
        data=json.dumps(body).encode('utf-8'),
        headers=headers,
        method='POST',
    )

    try:
        with urllib.request.urlopen(request, timeout=settings.AI_REQUEST_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', 'replace')[:300]
        raise LLMError(f'LLM HTTP {exc.code}: {detail}') from exc
    except urllib.error.URLError as exc:
        raise LLMError(f'LLM ulana olmadi: {exc.reason}') from exc
    except (ValueError, OSError) as exc:
        raise LLMError(f"LLM javob o'qilmadi: {exc}") from exc

    try:
        return payload['choices'][0]['message']['content'].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f'LLM javob formati buzilgan: {str(payload)[:200]}') from exc