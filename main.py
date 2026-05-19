import os
import asyncio

from openai import OpenAI

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

# ===== TOKENS =====

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")

client = OpenAI(api_key=OPENAI_KEY)

# ===== MEMORY =====

memory = {}

SYSTEM_PROMPT = """
Ты персональный AI помощник Армана.

Ты:
- умный
- дружелюбный
- технически грамотный
- помогаешь с электроникой
- помогаешь с ремонтом техники
- отвечаешь естественно
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

# ===== START =====

app = ApplicationBuilder().token(
    TELEGRAM_TOKEN
).build()

app.add_handler(
    MessageHandler(filters.TEXT, handle_text)
)

# ===== MAIN =====

async def main():

    print("AI ASSISTANT ONLINE")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    while True:
        await asyncio.sleep(60)

asyncio.run(main())