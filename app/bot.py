import os
import requests
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
from PIL import Image
from PIL.ExifTags import TAGS
import hashlib
import logging
import mimetypes
import asyncio
import threading
import time

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

BOT_NAME = "Telegram to Immich Bot"
BOT_VERSION = "0.6"

def validate_config():
    """Validate required environment variables."""
    missing_vars = []

    if not TELEGRAM_BOT_TOKEN:
        missing_vars.append("TELEGRAM_BOT_TOKEN")
    if not IMMICH_API_KEY:
        missing_vars.append("IMMICH_API_KEY")
    if not IMMICH_API_URL:
        missing_vars.append("IMMICH_API_URL")

    if not ALLOWED_USER_IDS:
        missing_vars.append("ALLOWED_USER_IDS")

    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

IMMICH_API_URL = os.getenv("IMMICH_API_URL", "http://your-immich-instance.ltd/api")
IMMICH_API_KEY = os.getenv("IMMICH_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

allowed_user_ids = os.getenv("ALLOWED_USER_IDS")
if not allowed_user_ids:
    raise ValueError("ALLOWED_USER_IDS environment variable is required")

ALLOWED_USER_IDS = [int(user_id.strip()) for user_id in allowed_user_ids.split(",") if user_id.strip()]
validate_config()

SUPPORTED_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.heic', '.heif', '.webp')
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS
SUPPORTED_FILE_TYPES = (
    "Images: JPG, PNG, GIF, BMP, TIFF, HEIC, WEBP\n"
    "Videos are not currently supported."
)

def get_file_type(file_path):
    """Determine file type based on extension and MIME type."""
    ext = os.path.splitext(file_path)[1].lower()
    mime_type, _ = mimetypes.guess_type(file_path)

    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        return "image"
    elif ext in SUPPORTED_VIDEO_EXTENSIONS:
        return "video"
    elif mime_type and mime_type.startswith('video/'):
        return "video"
    elif mime_type and mime_type.startswith('image/'):
        return "image"
    return "other"

def is_user_allowed(user_id):
    """Check if a user is allowed to upload files. If not set, all users can upload files"""
    if not ALLOWED_USER_IDS:
        return True
    return user_id in ALLOWED_USER_IDS

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

async def get_immich_status():
    """Check Immich server status and user info."""
    immich_status = "❌ Disconnected"
    user_info = "Unknown user"

    try:
        ping_response = requests.get(
            f"{IMMICH_API_URL}/server/ping",
            headers={'x-api-key': IMMICH_API_KEY},
            timeout=5
        )

        if ping_response.status_code == 200:
            immich_status = f"✅ Connected to Immich ({IMMICH_API_URL})"

            # If reachable, get user info
            try:
                user_response = requests.get(
                    f"{IMMICH_API_URL}/users/me",
                    headers={'x-api-key': IMMICH_API_KEY},
                    timeout=5
                )
                if user_response.status_code == 200:
                    user_data = user_response.json()
                    user_info = f"👤 {user_data.get('name', 'Unknown')}"
                    if user_data.get('isAdmin', False):
                        user_info += " [Admin]"
            except Exception as e:
                logger.error(f"Failed to get user info: {e}")
                user_info = "⚠️ Could not retrieve user info"
        else:
            immich_status = f"❌ Server ping failed (HTTP {ping_response.status_code})"

    except Exception as e:
        logger.error(f"Failed to connect to Immich: {e}")
        immich_status = f"❌ Connection failed: {str(e)}"

    return immich_status, user_info

async def send_startup_message(application: Application):
    """Send startup message to all allowed users when container starts."""
    immich_status, user_info = await get_immich_status()

    startup_message = (
        f"🤖 {BOT_NAME} v{BOT_VERSION} has started!\n\n"
        f"{immich_status}\n"
        f"Logged in as {user_info}\n\n"
        "Bot is ready to receive your files."
    )

    logger.info(f"Sending startup messages to {len(ALLOWED_USER_IDS)} allowed users")

    for user_id in ALLOWED_USER_IDS:
        try:
            await application.bot.send_message(
                chat_id=user_id,
                text=startup_message
            )
            logger.info(f"Successfully sent startup message to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send startup message to user {user_id}: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message with Immich connection status."""
    immich_status, user_info = await get_immich_status()

    help_message = (
        f"ℹ️ {BOT_NAME} v{BOT_VERSION}\n\n"
        f"{immich_status}\n"
        f"Logged in as {user_info}\n\n"
        "Available commands:\n"
        "/help - Show this help message\n"
        "/version - Show bot version\n"
        "/files - Show supported file types\n\n"
        "Send me files and I'll upload them to your Immich instance!"
    )

    await update.message.reply_text(help_message)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Alias for help command."""
    await help_command(update, context)


async def version(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the bot version when the command /version is issued."""
    await update.message.reply_text(f"📋 {BOT_NAME} version: {BOT_VERSION}")

async def files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send supported file types when the command /files is issued."""
    await update.message.reply_text(f"📄 Supported file types:\n{SUPPORTED_FILE_TYPES}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document uploads with improved logging."""
    user_id = update.message.from_user.id
    username = update.message.from_user.username or update.message.from_user.first_name
    file_name = update.message.document.file_name

    logger.info(f"Processing file upload from user {username} (ID: {user_id}): {file_name}")

    try:
        # Check user permission
        if not is_user_allowed(user_id):
            logger.warning(f"Unauthorized upload attempt by user {username} (ID: {user_id})")
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return

        document = update.message.document
        file_id = document.file_id
        temp_file_path = f"/tmp/{file_id}_{file_name}"

        logger.info(f"Downloading file {file_name} from Telegram")
        file = await context.bot.get_file(file_id)
        await file.download_to_drive(temp_file_path)

        if not os.path.exists(temp_file_path):
            logger.error(f"Failed to download file {file_name} from Telegram")
            await update.message.reply_text("❌ Failed to download file.")
            return

        # Check file type
        file_type = get_file_type(file_name)
        if file_type == "video":
            logger.warning(f"User {username} (ID: {user_id}) attempted to upload unsupported video file: {file_name}")
            await update.message.reply_text("ℹ️ Video files are not currently supported. Upload cancelled.")
            return
        elif file_type == "other":
            logger.warning(f"User {username} (ID: {user_id}) attempted to upload unsupported file type: {file_name}")
            await update.message.reply_text("❌ Unsupported file type. Only images are currently supported.")
            return

        # Process supported files
        file_size = os.path.getsize(temp_file_path)
        logger.info(f"Processing {file_type} file: {file_name} ({file_size} bytes)")

        try:
            if file_type == "image":
                file_created_at, file_modified_at = get_image_metadata(temp_file_path)
                logger.info(f"Successfully extracted metadata from image {file_name}")
            else:
                now = datetime.now(timezone.utc)
                file_created_at = format_iso_date(now)
                file_modified_at = format_iso_date(now)

            # Prepare and send request
            device_asset_id = f"{file_name}-{file_size}"
            checksum = calculate_sha1(temp_file_path)
            logger.info(f"Calculated checksum {checksum} for file {file_name}")

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

                logger.info(f"Uploading file {file_name} to Immich")
                response = requests.post(
                    f"{IMMICH_API_URL}/assets",
                    headers=headers,
                    files=files,
                    data=data
                )

                if response.status_code in (200, 201):
                    response_data = response.json()
                    if response.status_code == 200 and response_data.get('status') == 'duplicate':
                        logger.info(f"File {file_name} is a duplicate in Immich")
                        await update.message.reply_text(f"ℹ️ File {file_name} already exists in Immich.")
                    else:
                        logger.info(f"Successfully uploaded file {file_name} to Immich")
                        await update.message.reply_text(f"✅ File {file_name} uploaded successfully!")
                else:
                    logger.error(f"Failed to upload file {file_name} to Immich. Status code: {response.status_code}, Response: {response.text}")
                    await update.message.reply_text(f"❌ Failed to upload file. Error: {response.text}")

        except UnidentifiedImageError:
            logger.error(f"Could not identify image file: {file_name}")
            await update.message.reply_text("⚠️ Could not process this image file. It might be corrupted or in an unsupported format.")
        except Exception as e:
            logger.error(f"Error processing file {file_name}: {str(e)}", exc_info=True)
            await update.message.reply_text(f"❌ An error occurred: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error processing file {file_name} for user {username}: {str(e)}", exc_info=True)
        await update.message.reply_text("❌ An unexpected error occurred. Please try again later.")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.info(f"Cleaned up temporary file: {temp_file_path}")

def main():
    """Start the bot with command handlers."""
    try:
        validate_config()

        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        logging.getLogger("httpx").setLevel(logging.WARNING)

        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("version", version))
        application.add_handler(CommandHandler("files", files))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            asyncio.create_task(send_startup_message(application))
        else:
            loop.run_until_complete(send_startup_message(application))

        logger.info(f"{BOT_NAME} v{BOT_VERSION} started successfully")
        logger.info(f"Allowed users: {ALLOWED_USER_IDS}")

        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    main()
