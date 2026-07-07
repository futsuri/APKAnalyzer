FROM python:3.11-slim-bookworm

ARG APKTOOL_VERSION=3.0.2
ARG JADX_VERSION=1.5.5
ARG POETRY_VERSION=1.8.5

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    APKTOOL_PATH=/usr/local/bin/apktool \
    JADX_PATH=/opt/jadx/bin/jadx \
    JAVA_PATH=/usr/bin/java

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        openjdk-17-jre-headless \
        unzip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_${APKTOOL_VERSION}.jar" -o /usr/local/bin/apktool.jar \
    && printf '#!/bin/sh\nexec java -jar /usr/local/bin/apktool.jar "$@"\n' > /usr/local/bin/apktool \
    && chmod +x /usr/local/bin/apktool

RUN curl -fsSL "https://github.com/skylot/jadx/releases/download/v${JADX_VERSION}/jadx-${JADX_VERSION}.zip" -o /tmp/jadx.zip \
    && mkdir -p /opt/jadx \
    && unzip -q /tmp/jadx.zip -d /opt/jadx \
    && chmod +x /opt/jadx/bin/jadx \
    && rm /tmp/jadx.zip

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock* ./
RUN poetry install --only main --no-root

COPY . .

RUN mkdir -p /app/data/input/apks /app/data/output/static /app/data/output/dynamic /app/data/temp

ENTRYPOINT ["poetry", "run", "python", "main.py"]
CMD ["--help"]
