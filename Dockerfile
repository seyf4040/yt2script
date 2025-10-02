FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY database.py .
COPY ui.py .
COPY start.sh .

# Copy Streamlit config
COPY .streamlit .streamlit

# Make start script executable
RUN chmod +x start.sh

# Expose ports
EXPOSE 8080 8501

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the start script
CMD ["./start.sh"]