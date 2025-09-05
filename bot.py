import os
import asyncio
import yt_dlp
from fastapi import FastAPI, Request
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ------------------------
# Configuration
# ------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DOWNLOAD_DIR = "downloads"

# Ensure downloads folder exists
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# ------------------------
# Telegram Bot Handlers
# ------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username or update.effective_user.first_name
    await update.message.reply_text(f"Hello @{username}! Welcome to Cloud Music 🎵")

async def search_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if not query:
        await update.message.reply_text("Please type a song name to search!")
        return

    # Show searching message
    await update.message.reply_text(f"🔎 Searching for '{query}'...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_AUDIO)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=True)['entries'][0]
            filename = ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3")

            # Send audio
            await update.message.reply_audio(audio=open(filename, 'rb'), title=info['title'])

            # Delete after sending
            if os.path.exists(filename):
                os.remove(filename)
    except Exception:
        await update.message.reply_text("❌ Sorry, could not find or download the song.")

# ------------------------
# FastAPI App and Telegram Application
# ------------------------
app = FastAPI()
application = ApplicationBuilder().token(BOT_TOKEN).build()

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_song))

# ------------------------
# Webhook Endpoint
# ------------------------
@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, application.bot)
    await application.update_queue.put(update)
    return {"ok": True}

# ------------------------
# Optional Root Route
# ------------------------
@app.get("/")
async def home():
    return {"message": "Cloud Music Bot is running!"}

# ------------------------
# Start the Telegram Application properly
# ------------------------
async def start_bot():
    await application.initialize()
    await application.start()
    print("Telegram bot started and running...")

# Run both FastAPI and Telegram bot
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(start_bot())

# ------------------------
# Optional: Run locally with uvicorn
# ------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bot:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
