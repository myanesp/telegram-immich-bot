FROM python:3.13-alpine

LABEL org.opencontainers.image.title="Telegram to Immich bot"
LABEL org.opencontainers.image.description="Telegram bot to upload files directly to your Immich instance"
LABEL org.opencontainers.image.authors="Mario Yanes <mario.yanes@uc3m.es> (@myanesp)"
LABEL org.opencontainers.image.url=https://github.com/myanesp/telegram-immich-bot/blob/main/README.md
LABEL org.opencontainers.image.documentation=https://github.com/myanesp/telegram-immich-bot
LABEL org.opencontainers.image.source = "https://github.com/myanesp/telegram-immich-bot"
LABEL org.opencontainers.image.licenses="AGPL-3.0-or-later"

WORKDIR /app

RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libjpeg-turbo-dev \
    zlib-dev \
    libffi-dev \
    openssl-dev \
    postgresql-dev \
    libwebp-dev \
    tiff-dev \
    freetype-dev \
    lcms2-dev \
    openjpeg-dev \
    harfbuzz-dev \
    && apk add --no-cache \
    ffmpeg \
    && pip install --no-cache-dir --upgrade pip

COPY app/ /app

RUN pip install --no-cache-dir -r requirements.txt

RUN apk del .build-deps

CMD ["python", "bot.py"]
