# Telegram to Immich Bot

[![GitHub](https://badgen.net/badge/icon/github?icon=github&label)](https://github.com/myanesp/telegram-immich-bot)
[![Docker](https://badgen.net/badge/icon/docker?icon=docker&label)](https://hub.docker.com/r/myanesp/telegram-immich-bot)
[![Docker Pulls](https://badgen.net/docker/pulls/myanesp/telegram-immich-bot?icon=docker&label=pulls)](https://hub.docker.com/r/myanesp/telegram-immich-bot)
[![Last Commit](https://img.shields.io/github/last-commit/myanesp/telegram-immich-bot)](https://github.com/myanesp/telegram-immich-bot)
[![License](https://badgen.net/github/license/myanesp/telegram-immich-bot)](LICENSE)
[![Project Status: Active](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)

## Why?

This Docker container provides a simple way to automatically upload files from Telegram to your Immich photo management system. It's perfect for:

- Images and photos sent without compression that your relatives send you via Telegram
- Automatically backing up photos/videos sent to a Telegram bot
- Creating a simple upload pipeline for your personal media

## Features

- ✅ Automatic file uploads from Telegram to Immich
- ✅ Preserves original file metadata (for images sent as Documents)
- ✅ User restriction control (only allow specific Telegram user IDs)
- ✅ Simple configuration via environment variables

## How to Run

1. **Set up your Telegram bot**:
   - Create a new bot using [@BotFather](https://t.me/BotFather)
   - Note down your bot token
   - Start a chat with your new bot

2. **Configure your Immich instance**:
   - Ensure your Immich API is accessible from the host
   - Generate an API key from your Immich settings

3. **Run the container and send a file!**
This image is available both on [Docker Hub](https://hub.docker.com/r/myanesp/telegram-immich-bot) and [GitHub Container Registry](https://github.com/myanesp/telegram-immich-bot), so you're free to choose from which one you're going to download the image. Edit the following docker compose/docker run command to match your needs and you are ready to go! Remember to send the image(s) as File/Documents and not as Picture to preserve all metadata.

### Run with Docker Compose

```yaml
services:
  telegram-immich-bot:
    image: ghcr.io/myanesp/telegram-immich-bot:latest # or myanesp/telegram-immich-bot
    container_name: telegram-immich-bot
    restart: unless-stopped
    environment:
      - TELEGRAM_BOT_TOKEN=your_telegram_bot_token
      - IMMICH_API_URL=https://your-immich-instance.tld/api
      - IMMICH_API_KEY=your_immich_api_key
      - ALLOWED_USER_IDS=user1_id,user2_id
      - TZ=Europe/Madrid
```
### Run with Docker run

```yaml
docker run -d \
  --name telegram-immich-bot \
  --restart unless-stopped \
  -e TELEGRAM_BOT_TOKEN=your_telegram_bot_token \
  -e IMMICH_API_URL=http://your-immich-instance/api \
  -e IMMICH_API_KEY=your_immich_api_key \
  -e ALLOWED_USER_IDS=user1_id,user2_id \ 
  ghcr.io/myanesp/telegram-immich-bot:latest # or myanesp/telegram-immich-bot
```

## Environment Variables

| VARIABLE | MANDATORY | DESCRIPTION | DEFAULT |
|----------|:---------:|-------------------------------------------------------------|---------|
| TELEGRAM_BOT_TOKEN | ✅ | Your Telegram bot token obtained from @BotFather | - |
| IMMICH_API_URL | ✅ | Full URL to your Immich API endpoint (can be local or public) (e.g., `http://your-immich-instance:2283/api`) | - |
| IMMICH_API_KEY | ✅ | API key for authenticating with your Immich instance | - |
| ALLOWED_USER_IDS | ✅ | Comma-separated list of Telegram user IDs allowed to use the bot (e.g., `123456789,987654321`) | - |

## Planned features

- [ ] Upload videos
- [ ] Multiarch support
- [ ] Multilingual support
- [ ] Reduce Docker image size
