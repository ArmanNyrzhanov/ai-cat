from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

from openai import OpenAI

# ===== TOKENS =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")

client = OpenAI(api_key=OPENAI_KEY)

# ===== память =====
memory = {}

# ===== GPT =====
async def ask_gpt(user_id, text):

    if user_id not in memory:
        memory[user_id] = []

    memory[user_id].append({
        "role": "user",
        "content": text
    })

    messages = [
        {
            "role": "system",
            "content":
            "Ты милый AI кот-помощник. "
            "Ты дружелюбный, умный и иногда ведешь себя как кот."
        }
    ]

    messages.extend(memory[user_id])

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

# ===== PHOTO =====
async def handle_photo(update: Update,
                       context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "😺 Я пока учусь анализировать картинки"
    )

# ===== START =====
app = ApplicationBuilder().token(
    TELEGRAM_TOKEN
).build()

app.add_handler(
    MessageHandler(filters.TEXT, handle_text)
)

app.add_handler(
    MessageHandler(filters.PHOTO, handle_photo)
)

print("AI CAT ONLINE")

app.run_polling()