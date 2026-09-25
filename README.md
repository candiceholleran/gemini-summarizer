# Gemini API File Summarizer & Evaluator (Python)

A robust, enterprise-grade Python script integrating with the Google GenAI SDK (`google-genai`) to perform batch document summarization and automated quality evaluation (LLM-as-a-Judge) with built-in fault tolerance.

## Features
- **Batch Processing**: Automatically iterates through all `.txt` files in a target directory (`./documents`).
- **Automated Quality Evaluation (LLM-as-a-Judge)**: Executes a secondary evaluation pass for every generated summary to grade:
  - **Accuracy (1–5)**: Checks for factual inconsistencies or hallucinations against the original source.
  - **Coverage (1–5)**: Evaluates retention of key document points.
  - **Justification**: Generates a structured one-line explanation for the assigned scores.
- **Fault-Tolerant Execution**: Employs per-file exception handling and exponential backoff (`tenacity`) to prevent transient server-side 503 capacity errors or file errors from breaking batch execution.
- **Multi-Format Export**: Consolidates results into a structured Markdown report (`batch_summary_results.md`) and logs evaluation metrics to a CSV (`eval_results.csv`).
- **Environment Security**: Loads API credentials securely via environment variables (`GEMINI_API_KEY`).

## Tech Stack
- **Python 3.12**
- **Google GenAI SDK** (`google-genai`)
- **Tenacity** (Retry and backoff logic)

## Getting Started

1. **Install dependencies**:
   ```bash
   pip install google-genai tenacity