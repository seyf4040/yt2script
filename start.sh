#!/bin/bash

# Start Flask API in the background
echo "Starting Flask API on port 8080..."
gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 300 app:app &

# Wait a moment for Flask to start
sleep 3

# Start Streamlit on port 8501
echo "Starting Streamlit UI on port 8501..."
streamlit run ui.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true

# Keep container running
wait