#!/bin/bash
# Install dependencies
pip install -r requirements.txt

# Run FastAPI
uvicorn app.main:app --host 0.0.0.0 --port $PORT