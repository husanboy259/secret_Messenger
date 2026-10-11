# ROADMAP_AI_BOT.md — Support / AI yordamchi (backend)

Bu hujjat **AI support botining back-end rejasini** batafsil bayon qiladi.
Siz (`AI` integrator) shu reja bo'yicha ishlaysiz. `chats/bot.py` dagi
`route_bot_reply()` — aynan shu funksiyaga AI ulash uchun tayyor bo'sh hook.

> Hozirgi holat: har foydalanuvchiga «Messger Support» bot chati **allaqachon
> avto-yaratiladi** (ro'yxat yuklanganda va ro'yxatdan o'tishda). Bot chat oddiy
> 1:1 chat kabi ko'rinadi va «Bots»/«All Chats» papkalarida turadi. Xabar kelganda
> `route_bot_reply()` chaqiriladi (WS ham, REST ham). Faqat AI javob yaratish qoldi.

---

## 1. Maqsadlar

1. Har foydalanuvchining «Messger Support» chatida realtime AI javob.
2. Javob oddiy chat xabari bo'lib ko'rinadi (optimistik + `message.new` broadcast).
3. Yangi va eski sign-up qilgan har kimda shu chat bor.
4. Operator/human handoff imkoniyati (AI bilmasa → insonga).
5. Xavfsizlik: prompt-injection, moderação, xarajat cheklovi, log/audit.

---

## 2. Arxitektura qatlamlari

```
User (frontend) ── WS /api/ws/chat/<id>/ ──▶ ChatConsumer
                                              │  message.create → Message DB
                                              ▼
                                   hook_bot_reply(chat, message)  ← siz shu yerga kirasiz
                                              │
                        ┌─────────────────────┼──────────────────────┐
                        ▼                     ▼                      ▼
                 Intent router           RAG (bilim baza)        Human handoff
                 (kiyingi LLM yoki       │  vaqt DB (pgvector)   (eskalatsiya)
                  klassifikator)         ▼                        │
                                   context + conversation        ▼
                        ┌──────────────▼──────────────┐    SupportWorker (AQ/round-robin)
                        ▼                             ▼
                 AI provider (LLM)            Moderatsiya/guardrail
                        │                    (kirish + chiqish tekshiruvi)
                        ▼
                 Javob yoziladi Message(chat, sender=bot) ──▶ realtime broadcast
```

**Muhim tamoyillar (2026 best practice):**
- RAG: chunk + embed → pgvector → top-k retrieve → **reranker** → top-n + citation.
- Streaming: token-token oqayotganda broadcast (latency sezilmasligi uchun).
- Guardrails ikki tomonda: input (jailbreak/prompt-injection) va output (topik/harflar).
- Har suhbat = trace (observability), skorli evaluatorlar bilan.
- Model/hujjatlar bergan raqam va siyosatlarni «isbotli javob» qilib qaytarma — citation bilan.

---

## 3. Yangi modellar (migration bilan)

`chats/models.py` ga (yoki yangi `support` app) qo'shish:

```python
class BotConversation(models.Model):
    chat = models.OneToOneField(Chat, on_delete=models.CASCADE, related_name='bot_conv')
    summary = models.TextField(blank=True)              # kechagi kontekst xulosasi
    state = models.CharField(max_length=20, default='open')  # open|awaiting_agent|closed
    agent = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

class KnowledgeDoc(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()                        # chunk-embed Dan keyin
    source = models.CharField(max_length=255, blank=True)
    embedding = models.JSONField(null=True, blank=True) # yoki alohida vector table
    updated_at = models.DateTimeField(auto_now=True)

class BotLog(models.Model):                             # audit / trace
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    event = models.CharField(max_length=50)             # user_msg / ai_resp / error / escalate
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
```

Maslahat: RAG embeddings uchun alohida `pgvector` extension (yangi field emas)
yoki engil davr uchun `django-pgvector` / `pgvector/django` yoki Pinecone/Weaviate.
Kichik xajmda embeddings JSONField da saqlanib, `numpy` bilan qidirish ham yetarli.

---

## 4. `chats/bot.py` — ulanish nuqtasi

`route_bot_reply(chat, message)` delarini to'ldirasiz:

```python
def route_bot_reply(chat, message):
    if not chat.is_bot:
        return None
    if not settings.AI_ENABLED:            # kalit kaliti kalitsiz rejim
        return None
    # 1) faqat user yuborgan xabarga javob (bot o'z javobini qayta ishlamaydi)
    if message.sender.username == SUPPORT_USERNAME:
        return None
    # 2) konversatsiya oqimini qo'zg'atish (queue / task)
    from .ai.tasks import enqueue_reply
    enqueue_reply(chat.id, message.id)
```

### Konkurentlik/multi-worker
`route_bot_reply` blogida `queue`: Celery (Redis broker) yoki `asyncio` consumer.
Frontend streaming talab qilmasa ham, javob **keyingi WS/global** realtime
orqali boradi — DMES shuning uchun `Message(sender=bot)` ni yaratib,
`channel_layer.group_send('chat_<id>', chat.message)` + `notify_message_created`
qilish kerak (already-mavjud printsiplar).

---

## 5. AI integratsiya API (provayder abstraksiyasi)

`chats/ai/provider.py`:

```python
class LLMClient:
    def __init__(self):  # OpenAI-compatible endpoint; cloud yoki self-host
        ...
    def generate(self, prompt, history, stream=False):
        ...
    def embed(self, text) -> list[float]:
        ...
```

- Boshlang'ich davr: **OpenAI-compatible** (GPT-4o-mini / Claude / Llama — kalitga qarab).
- `settings.py`: `AI_ENABLED`, `AI_API_KEY`, `AI_MODEL`, `AI_EMBED_MODEL`,
  `AI_MAX_TOKENS`, `AI_DAILY_BUDGET`, `AI_CONTEXT_LEN`.
- Javob xarajati: har xabar uchun token hisobi → `BotLog` ga yozing.
- Fallback: provider ishlamasa (quota/network) — «ozgina keyinroq yozaman» ekan
  yoki human handoff.

### Konversatsiya konteksti (xotira)
- So'nggi N xabar (`Message.objects.filter(chat=..., order_by='-created_at')[:N]`)
- + `BotConversation.summary` (eski qism xulosasi) — context window cheklovini
  chetlab o'tish uchun.
- Ebadi havola: har javobda `BotLog` trace qilish.

---

## 6. RAG (bilimlar bazasi) — best practice 2026

1. **Ingest**: markdown/HTML/PDF → semantic yoki recursive chunk (512–1024 token, overlap 10–15%).
2. **Embed**: `AI_EMBED_MODEL` (masalan `text-embedding-3-large`) → vektor saqla.
3. **Retrieve**: top-k=5 `cosine similarity`.
4. **Rerank**: dedicated reranker bilan top-3 ga toraytir (precision +4–6% beradi).
5. **Citation**: javobda foydalanilgan chunk meta ma'lumoti (title/section) — 
   yetkazilgan hanuz u „faithfulness" evaluatsiyasi uchun kerak bo'ladi.
6. **Prompt-injection**: chunk tarkibidan ko'rsatmalar o'qimasin — system promptda
   «berilgan hujjatdan tashqari ma'lumot ishlatmang».

Bilim manbalari: FAQ, qo'llanma, siyosat hujjatlari (admin panel orqali yuklanadi).

---

## 7. Guardrails / moderatsiya

- **Input**: uzunlik cheklovi, `deny-list` (haqorat, shaxsiy data), jailbreak
  naqshlari filter (regex + lightweight model).
- **Output**: model javobi yo'na qaytmasin (Llama Guard / Guardrails AI /
  NeMo Guardrails), ruxsat etilmagan mavzu (masalan «kod yoz», «Boshqa saytga
  kir») → standart «Bu sohada yordam bera olmayman».
- **Rate limit**: foydalanuvchi boshiga daqiqada N xabar; global soatlik budget.
- **Human handoff**: bot noaniq/eskalatsiya belgisini ko'rsa → `bot.state='awaiting_agent'`,
  javob: «Operator ulayapman…» + supervisor chat paneli (admin/agent) uchun placeholder.

---

## 8. Realtime yetkazish (mavjud tizim bilan)

Har bir AI javob:

```python
data = MessageSerializer(bot_msg).data
async_to_sync(get_channel_layer().group_send)(
    f'chat_{chat.id}', {'type': 'chat.message', 'payload': data}
)
notify_message_created(chat, bot.id, data)   # chat ro'yxati preview yangilanadi
```

Bu `chats/consumers.py` ning allaqachon ishlaydigan `handleSocket → upsertMessage`
bilan ochiq oynada realtime ko'rsatadi. Frontend **o'zgartirmasdan** ishlaydi
(mavjud `message.new` oqimi bot xabarini oddiy xabar sifatida qabul qiladi).

### Streaming (ixtiyoriy, keyinroq)
Variant: AI token-token javob qaytarayotganda har N token `message.edit`-cha
yuborish — bu talab qilinsa `ChatConsumer` ga `message.patch` action qo'shiladi.
Birinchi versiya uchun to'liq javob yetarli.

---

## 9. Observability / eval / cost

- **Trace**: har suhbat `BotLog` (parent→span): user_msg, retrieval chunks, model call, output, skor.
- **Evaluatorlar (haftalik)**: faithfulness (citation ushlanganmi), harmless,
  helpfulness. `ai-evaluation` / Arize Phoenix / OTLP.
- **Skor past suhbatlar** → ularni label (retrieval miss / prompt / hallucination).
- **Xarajat**: kunlik/oylik budget, model tanlash (mini modellar), embedding cache.

---

## 10. Xavfsizlik

- API kalitlar server env-da (frontendga tushmaydi).
- AI-endpoint CORS/mikrozona: Frontend to'g'ridan-to'g'ri providerga kirmaydi.
- PII (shaxsiy ma'lumot) logda qisqartiriladi (redaction), retention siyosati.
- Bugunlik hujjatlar bilan ishlash — permission tekshiruvi (faqat admin yuklaydi).
- Output sandbox: agent tool call bo'lsa — ishlatiladigan buyruqlar katalogi cheklanadi.

---

## 11. Faza rejasi (tavsiya)

| Faza | Vazifa | Natija |
|---|---|---|
| 1 | `LLMClient` + `route_bot_reply` enqueue; oddiy echo/prompt javob | AI javob realtime ishlaydi |
| 2 | Konversatsiya konteksti (N xabar + summary); typing indikator | Multi-turn suhbat |
| 3 | RAG: KnowledgeDoc + ingest + retrieve + rerank + citation | Bilimdan izchil javob |
| 4 | Guardrails (input/output), rate-limit, human handoff | Xavfsiz va moderatsiyali |
| 5 | BotLog trace + evaluatorlar + budget | Monitoring, sifat, xarajat nazorati |
| 6 | Streaming (message.patch), ayrim admin panel (javob yuklash/history) | Polished UX |

### Testlar
- Unit: `route_bot_reply` (faqat user msg, faqat is_bot), context build, chunk.
- Integration: WS bilan user yozadi → bot javob `message.new` keladi.
- Evaluation dataset: 50–100 so'rov (FAQ), har faza skor ko'rsatkichi.

---

## 12. Deploy (Render/Yexcel)

- Render free: Celery worker + Redis kerak bo'lsa ~Free tier yetishmaydi →
  boshlang'ich faza `route_bot_reply` ni `threading`/`asyncio` bilan bitta processda
  odatiy yechim; Redis faqat multi-worker shartida (endpoint `REDIS_URL`).
- `channels_redis` allaqachon requirements'da; `REDIS_URL` berilsa WS layer Redis'ga
  o'tadi (config/settings.py).

---

Eslatma: `chats/bot.py` hozirgi `route_bot_reply` — log yozadi va `None` qaytaradi.
Faza 1 natijasi sifatida shu funksiyani to'ldiring va `AI_ENABLED=True` qiling.