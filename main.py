import os
import asyncio
import tempfile
import base64

from openai import OpenAI

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

# =====================================================
# TOKENS
# =====================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")

client = OpenAI(api_key=OPENAI_KEY)

# =====================================================
# MEMORY
# =====================================================

memory = {}

SYSTEM_PROMPT = """
Ты персональный AI помощник Армана.

Ты:
- умный
- дружелюбный
- технически грамотный
- помогаешь с электроникой
- помогаешь с ремонтом техники
- можешь анализировать схемы и платы
- отвечаешь естественно
- помнишь контекст разговора

Отвечай кратко и по делу.
Не добавляй лишнюю воду.
"""

# =====================================================
# GPT
# =====================================================

async def ask_gpt(user_id, text):

    if user_id not in memory:
        memory[user_id] = []

    memory[user_id].append({
        "role": "user",
        "content": text
    })

    messages = [{
        "role": "system",
        "content": SYSTEM_PROMPT
    }]

    messages.extend(memory[user_id][-20:])

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    answer = response.choices[0].message.content

    memory[user_id].append({
        "role": "assistant",
        "content": answer
    })

    return answer

# =====================================================
# TEXT
# =====================================================

async def handle_text(update: Update,
                      context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    text = update.message.text

    await update.message.chat.send_action("typing")

    answer = await ask_gpt(user_id, text)

    await update.message.reply_text(answer)

# =====================================================
# VOICE
# =====================================================

async def handle_voice(update: Update,
                       context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    await update.message.chat.send_action("record_voice")

    try:

        # ============================================
        # DOWNLOAD VOICE
        # ============================================

        voice = await update.message.voice.get_file()

        temp_ogg = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".ogg"
        )

        await voice.download_to_drive(temp_ogg.name)

        # ============================================
        # STT
        # ============================================

        with open(temp_ogg.name, "rb") as audio:

            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio
            )

        text = transcript.text

        print("VOICE:", text)

        # ============================================
        # GPT
        # ============================================

        answer = await ask_gpt(user_id, text)

        # ============================================
        # TTS
        # ============================================

        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=answer
        )

        temp_mp3 = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".mp3"
        )

        speech.stream_to_file(temp_mp3.name)

        # ============================================
        # SEND VOICE
        # ============================================

        with open(temp_mp3.name, "rb") as audio:

            await update.message.reply_voice(audio)

        # ============================================
        # CLEANUP
        # ============================================

        os.remove(temp_ogg.name)
        os.remove(temp_mp3.name)

    except Exception as e:

        print("VOICE ERROR:", e)

        await update.message.reply_text(
            f"Ошибка voice: {e}"
        )

# =====================================================
# PHOTO / VISION
# =====================================================

async def handle_photo(update: Update,
                       context: ContextTypes.DEFAULT_TYPE):

    try:

        await update.message.chat.send_action("typing")

        photo = update.message.photo[-1]

        file = await photo.get_file()

        temp_img = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".jpg"
        )

        await file.download_to_drive(temp_img.name)

        # ============================================
        # BASE64
        # ============================================

        with open(temp_img.name, "rb") as image_file:

            base64_image = base64.b64encode(
                image_file.read()
            ).decode("utf-8")

        # ============================================
        # VISION GPT
        # ============================================

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
Ты профессиональный технический AI помощник.

Анализируй изображения кратко и по делу.

Правила:
- не описывай фон
- не описывай стол
- не описывай очевидные вещи
- не добавляй воду
- не пиши догадки без причины
- концентрируйся на главном объекте

Если это электроника:
- определяй устройство
- ищи неисправности
- анализируй пайку
- анализируй компоненты
- помогай с ремонтом

Отвечай как инженер.
"""
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """
Определи главное устройство или объект.
Дай только полезный технический анализ.
Без лишнего описания окружения.
"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url":
                                f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )

        answer = response.choices[0].message.content

        await update.message.reply_text(answer)

        os.remove(temp_img.name)

    except Exception as e:

        print("VISION ERROR:", e)

        await update.message.reply_text(
            f"Ошибка vision: {e}"
        )

# =====================================================
# APP
# =====================================================

app = ApplicationBuilder().token(
    TELEGRAM_TOKEN
).build()

# =====================================================
# HANDLERS
# =====================================================

app.add_handler(
    MessageHandler(filters.TEXT, handle_text)
)

app.add_handler(
    MessageHandler(filters.VOICE, handle_voice)
)

app.add_handler(
    MessageHandler(filters.PHOTO, handle_photo)
)

# =====================================================
# MAIN
# =====================================================

async def main():

    print("AI ASSISTANT ONLINE")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    while True:
        await asyncio.sleep(60)

asyncio.run(main())