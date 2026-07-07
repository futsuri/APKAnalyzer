FROM python:3.11-slim

# Install system dependencies, including OpenJDK 17
RUN apt-get update && apt-get install -y \
    openjdk-17-jre-headless \
    curl \
    unzip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Apktool 3.0.2
RUN curl -L https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool -o /usr/local/bin/apktool \
    && chmod +x /usr/local/bin/apktool \
    && curl -L https://github.com/iBotPeaches/Apktool/releases/download/v3.0.2/apktool_3.0.2.jar -o /usr/local/bin/apktool.jar \
    && chmod +x /usr/local/bin/apktool.jar

# Install JADX 1.5.5
RUN curl -L https://github.com/skylot/jadx/releases/download/v1.5.5/jadx-1.5.5.zip -o /tmp/jadx.zip \
    && mkdir -p /opt/jadx \
    && unzip /tmp/jadx.zip -d /opt/jadx \
    && ln -s /opt/jadx/bin/jadx /usr/local/bin/jadx \
    && rm /tmp/jadx.zip

# Set up working directory
WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry
RUN poetry config virtualenvs.create false

# Copy dependency definition
COPY pyproject.toml ./

# Install python dependencies
RUN poetry install --no-root --no-interaction --no-ansi

# Copy the rest of the application
COPY . .

# Set environment variables for global commands
ENV APKTOOL_PATH=apktool
ENV JADX_PATH=jadx
ENV JAVA_PATH=java

# Declare volumes for input and output data
VOLUME ["/app/data"]

ENTRYPOINT ["python", "main.py"]
