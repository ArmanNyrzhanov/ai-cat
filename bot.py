import os
import tempfile

from openai import OpenAI

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

# ===== CONFIG =====

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")

client = OpenAI(api_key=OPENAI_KEY)

# ===== MEMORY =====

memory = {}

SYSTEM_PROMPT = """
Ты персональный AI помощник Армана.

Твой характер:
- умный
- дружелюбный
- технически грамотный
- помогаешь с электроникой
- помогаешь с ремонтом мед оборудования
- можешь анализировать схемы и платы
- иногда ведешь себя как живой компаньон
- не перебарщиваешь с "мяу"

Ты помнишь контекст разговора.
Отвечай естественно.
"""

# ===== GPT =====

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

# ===== TEXT =====

async def handle_text(update: Update,
                      context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    text = update.message.text

    await update.message.chat.send_action("typing")

    answer = await ask_gpt(user_id, text)

    await update.message.reply_text(answer)

# ===== VOICE =====

async def handle_voice(update: Update,
                       context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    await update.message.chat.send_action("record_voice")

    voice = await update.message.voice.get_file()

    ogg_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".ogg"
    )

    await voice.download_to_drive(ogg_file.name)

    # ===== STT =====

    with open(ogg_file.name, "rb") as audio:

        transcript = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=audio
        )

    text = transcript.text

    print("VOICE:", text)

    answer = await ask_gpt(user_id, text)

    # ===== TTS =====

    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=answer
    )

    mp3_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp3"
    )

    speech.stream_to_file(mp3_file.name)

    # ===== SEND =====

    with open(mp3_file.name, "rb") as audio:

        await update.message.reply_voice(audio)

# ===== PHOTO =====

async def handle_photo(update: Update,
                       context: ContextTypes.DEFAULT_TYPE):

    await update.message.chat.send_action("typing")

    photo = update.message.photo[-1]

    file = await photo.get_file()

    image_path = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".jpg"
    )

    await file.download_to_drive(image_path.name)

    with open(image_path.name, "rb") as img:

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content":
                    "Ты технический AI помощник. "
                    "Анализируй изображения подробно."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text":
                            "Проанализируй это изображение"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url":
                                f"data:image/jpeg;base64,"
                            }
                        }
                    ]
                }
            ]
        )

    answer = response.choices[0].message.content

    await update.message.reply_text(answer)

# ===== START =====

app = ApplicationBuilder().token(
    TELEGRAM_TOKEN
).build()

app.add_handler(
    MessageHandler(filters.TEXT, handle_text)
)

app.add_handler(
    MessageHandler(filters.VOICE, handle_voice)
)

app.add_handler(
    MessageHandler(filters.PHOTO, handle_photo)
)

print("AI ASSISTANT ONLINE")

app.run_polling()