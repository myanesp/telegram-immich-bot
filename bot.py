import os
import requests
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from PIL import Image
from PIL.ExifTags import TAGS
import hashlib
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)

# Configuration from environment variables
IMMICH_API_URL = os.getenv("IMMICH_API_URL", "http://your-immich-instance.ltd/api")
IMMICH_API_KEY = os.getenv("IMMICH_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def format_iso_date(dt):
    """Format datetime as ISO 8601 with Z timezone."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

def get_image_metadata(file_path):
    """Extract metadata from image files."""
    try:
        with Image.open(file_path) as img:
            exif_data = img._getexif() or {}
            metadata = {TAGS.get(tag, tag): value for tag, value in exif_data.items()}

            if 'DateTimeOriginal' in metadata:
                created_at = datetime.strptime(metadata['DateTimeOriginal'], '%Y:%m:%d %H:%M:%S')
            elif 'DateTime' in metadata:
                created_at = datetime.strptime(metadata['DateTime'], '%Y:%m:%d %H:%M:%S')
            else:
                created_at = datetime.fromtimestamp(os.path.getmtime(file_path), timezone.utc)

            return format_iso_date(created_at), format_iso_date(datetime.now(timezone.utc))
    except Exception:
        now = datetime.now(timezone.utc)
        return format_iso_date(now), format_iso_date(now)

def calculate_sha1(file_path):
    """Calculate SHA1 checksum of a file."""
    sha1 = hashlib.sha1()
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document uploads to Immich."""
    try:
        if not update.message or not update.message.document:
            return

        document = update.message.document
        file_id = document.file_id
        file_name = document.file_name

        # Download file
        temp_file_path = f"/tmp/{file_id}_{file_name}"
        file = await context.bot.get_file(file_id)
        await file.download_to_drive(temp_file_path)

        if not os.path.exists(temp_file_path):
            await update.message.reply_text("❌ Failed to download file.")
            return

        # Handle metadata
        file_size = os.path.getsize(temp_file_path)
        if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')):
            file_created_at, file_modified_at = get_image_metadata(temp_file_path)
        else:
            now = datetime.now(timezone.utc)
            file_created_at = format_iso_date(now)
            file_modified_at = format_iso_date(now)

        # Request
        device_asset_id = f"{file_name}-{file_size}"
        checksum = calculate_sha1(temp_file_path)

        with open(temp_file_path, 'rb') as f:
            files = {'assetData': (file_name, f)}
            data = {
                'deviceAssetId': device_asset_id,
                'deviceId': 'telegram-bot-device',
                'fileCreatedAt': file_created_at,
                'fileModifiedAt': file_modified_at,
                'isFavorite': 'false',
                'visibility': 'timeline'
            }
            headers = {
                'x-api-key': IMMICH_API_KEY,
                'x-immich-checksum': checksum
            }

            response = requests.post(
                f"{IMMICH_API_URL}/assets",
                headers=headers,
                files=files,
                data=data
            )

        if response.status_code in (200, 201):
            try:
                response_data = response.json()
                if response.status_code == 200 and response_data.get('status') == 'duplicate':
                    logger.info("File %s is a duplicate", file_name)
                    await update.message.reply_text(f"ℹ️ File {file_name} already exists in Immich.")
                else:
                    logger.info("File %s uploaded successfully", file_name)
                    await update.message.reply_text(f"✅ File {file_name} uploaded successfully!")
            except ValueError:
                await update.message.reply_text("✅ File uploaded successfully!")
        else:
            logger.error("Upload failed with status code: %d", response.status_code)
            await update.message.reply_text(f"❌ Failed to upload file. Status code: {response.status_code}")

    except Exception as e:
        logger.error("Error processing file: %s", str(e), exc_info=True)
        await update.message.reply_text("❌ An error occurred during upload.")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def main():
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
