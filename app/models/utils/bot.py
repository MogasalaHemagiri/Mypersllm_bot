import os
import asyncio
import logging
from telethon import TelegramClient, events
from pyrogram import Client
from pymongo import MongoClient
from gridfs import GridFS
from app.processing import process_file, process_text
from app.database import save_to_csv_and_upload

# Logging setup
logging.basicConfig(level=logging.INFO)

# Load environment variables
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# MongoDB Connection
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["telegram_bot"]
fs = GridFS(db)

# Initialize Telegram Bot
bot = TelegramClient("bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Handle file uploads
@bot.on(events.NewMessage)
async def handle_files(event):
    if event.document or event.photo or event.audio or event.video:
        chat_id = event.chat_id
        file = await event.get_file()
        file_bytes = await bot.download_file(file)
        file_name = file.name or "file"

        # Store file in MongoDB
        fs.put(file_bytes, filename=file_name)

        # Process file asynchronously
        file_type = process_file(file_bytes, file.mime_type)
        
        # Save structured data
        csv_file_id = save_to_csv_and_upload([(file_name, file_type)], chat_id)
        await event.reply("✅ Data processed! Use `/get_csv` to download.")

# Handle text messages
@bot.on(events.NewMessage)
async def handle_text(event):
    text = event.message.message
    structured_data = process_text(text)
    chat_id = event.chat_id

    csv_file_id = save_to_csv_and_upload([("text_input", structured_data)], chat_id)
    await event.reply("✅ Text processed! Use `/get_csv` to download.")

# Retrieve CSV data
@bot.on(events.NewMessage(pattern="/get_csv"))
async def get_csv(event):
    chat_id = event.chat_id
    file_doc = db.fs.files.find_one({"filename": f"{chat_id}_structured_data.csv"})

    if file_doc:
        file_id = file_doc["_id"]
        file_data = fs.get(file_id).read()
        await bot.send_file(chat_id, file=file_data, filename="structured_data.csv")
    else:
        await event.reply("❌ No processed data found. Please send a file or text first!")

# Start bot
bot.run_until_disconnected()
