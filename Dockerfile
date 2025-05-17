FROM python:3.9-slim

# Install ffmpeg and build dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    libffi-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create user
RUN useradd -m -s /bin/bash bot

# Copy application files
WORKDIR /home/bot
COPY ./requirements.txt ./
COPY ./bot.py ./
COPY ./task.py ./
COPY ./telegram_progress.py ./
COPY ./backends/ ./backends/

# Install dependencies
RUN pip3 install --no-warn-script-location python-telegram-bot==13.0 && \
    pip3 install --no-warn-script-location beautifulsoup4 && \
    pip3 install --no-warn-script-location python-dotenv && \
    pip3 install --no-warn-script-location yt-dlp && \
    pip3 install --no-warn-script-location tqdm && \
    pip3 install --no-warn-script-location hurry.filesize && \
    pip3 install --no-warn-script-location pydrive2 && \
    pip3 install --no-warn-script-location requests

# Set user
USER bot

# Run
CMD ["python3", "./bot.py"]
