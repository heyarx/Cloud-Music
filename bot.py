import os
import yt_dlp
from fastapi import FastAPI, Request
from telegram import Update, ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ------------------------
# Configuration
# ------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Set this in Render environment
APP_URL = os.environ.get("APP_URL")      # Your Render URL, e.g., https://cloudsong-arx.onrender.com
DOWNLOAD_DIR = "downloads"

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

    msg = await update.message.reply_text(f"🔎 Searching for '{query}'...")
    
    # Show typing/uploading status
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
            
            # Delete file after sending
            os.remove(filename)
    except Exception as e:
        await update.message.reply_text("❌ Sorry, could not find or download the song.")

# ------------------------
# Set Up Application
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
# Set Webhook on Startup
# ------------------------
@app.on_event("startup")
async def set_webhook():
    webhook_url = f"{APP_URL}/webhook"
    await application.bot.set_webhook(url=webhook_url)
    print(f"Webhook set to: {webhook_url}")

# ------------------------
# Run Uvicorn locally (for testing)
# ------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bot:app", host="0.0.0.0", port=8000, reload=True)
