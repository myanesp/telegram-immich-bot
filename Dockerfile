FROM python:3.13-alpine

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

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

RUN apk del .build-deps

CMD ["python", "bot.py"]
