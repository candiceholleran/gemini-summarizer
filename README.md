# Gemini API File Summarizer (Python)

A robust Python script integrating with the Google GenAI SDK (google-genai) to summarize local text files with built-in fault tolerance.

## Features
- **Resilient Error Handling**: Implements exponential backoff retries using tenacity to manage transient server-side 503 capacity errors.
- **Model Fallback Chain**: Automatically cycles through available production Flash endpoints during high-demand spikes.
- **Environment Security**: Loads API credentials securely via environment variables (GEMINI_API_KEY).

## Tech Stack
- **Python 3.12**
- **Google GenAI SDK** (`google-genai`)
- **Tenacity** (Retry logic)

## Getting Started

1. Install dependencies:
   pip install google-genai tenacity

2. Set your environment variable (PowerShell):
   $env:GEMINI_API_KEY="your_api_key_here"

3. Add a text file named sample.txt to the root directory, then run:
   python app.py
