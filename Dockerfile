FROM python:3.9-slim

# Install system dependencies including rclone
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    libffi-dev \
    curl \
    unzip \
    && curl https://rclone.org/install.sh | bash \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create user early
RUN useradd -m -s /bin/bash bot

# Set working directory
WORKDIR /home/bot

# Copy only requirements first for better caching
COPY ./requirements.txt ./

# Install Python dependencies (this layer will be cached unless requirements.txt changes)
RUN pip3 install --no-cache-dir --no-warn-script-location -r requirements.txt

# Copy application code (this layer will rebuild on code changes, but deps won't)
COPY ./bot.py ./
COPY ./task.py ./
COPY ./telegram_progress.py ./
COPY ./backends/ ./backends/

# Set ownership of files to bot user
RUN chown -R bot:bot /home/bot

# Switch to bot user
USER bot

# Run the application
CMD ["python3", "./bot.py"]
