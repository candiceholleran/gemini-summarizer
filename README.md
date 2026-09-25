Multi-Model Comparative Summarization Pipeline
A production-ready Python batch processing pipeline that summarizes .txt documents using multiple LLM providers (Google Gemini and Groq / Meta Llama), evaluates performance using an LLM-as-a-Judge scoring system, and outputs comparative results.

Features
Multi-Model Batch Summarization: Summarizes text files across Google Gemini and Groq API endpoints.

Automated LLM-as-a-Judge Evaluation: Scores each summary on a 1–5 scale for:

Accuracy: Detection of factual errors or hallucinations.

Coverage: Capture of main key points.

Failover & Resilience:

Implements exponential backoff retries via tenacity.

Automatic model failover on 503 UNAVAILABLE capacity spikes.

Dual Output Formats:

Markdown Report (batch_summary_results.md): Side-by-side comparative table format.

CSV Dataset (eval_results.csv): Clean structured data for analytics.

Directory Structure
Plaintext
.
├── documents/                # Place target .txt files here
│   ├── sample1.txt
│   ├── sample2.txt
│   └── sample3.txt
├── app.py                    # Main pipeline entrypoint
├── batch_summary_results.md  # Generated comparative Markdown report
├── eval_results.csv          # Generated evaluation metrics CSV log
├── requirements.txt          # Dependencies
└── README.md
Prerequisites & Installation
1. Clone the Repository
Bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
2. Set Up Virtual Environment
Bash
python -m venv venv

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# On macOS / Linux:
source venv/bin/activate
3. Install Dependencies
Create a requirements.txt file containing:

Plaintext
google-genai
groq
tenacity
Install them via pip:

Bash
pip install -r requirements.txt
Environment Variables Configuration
Set your API keys as environment variables before running the script:

Windows (PowerShell)
PowerShell
$env:GEMINI_API_KEY="your_google_gemini_api_key"
$env:GROQ_API_KEY="your_groq_api_key"
macOS / Linux (Bash)
Bash
export GEMINI_API_KEY="your_google_gemini_api_key"
export GROQ_API_KEY="your_groq_api_key"
Usage
Place Documents: Put one or more .txt files into the ./documents directory.

Execute the Pipeline:

Bash
python app.py
Output Preview
Console Output
Plaintext
Found 3 file(s) for multi-model comparison.

[1/3] Processing: sample1.txt...
  ├─ Generating Gemini summary...
  ├─ Evaluating Gemini summary...
  ├─ Generating Groq summary...
  ├─ Evaluating Groq summary...
  └─ Complete! Gemini: 5/5 | Groq: 5/4

Comparative batch pipeline complete!
  ├─ Markdown report: 'batch_summary_results.md'
  └─ CSV metrics log: 'eval_results.csv'
Markdown Output (batch_summary_results.md)
Markdown
# Multi-Model Comparative Summarization Report

Comparing **Gemini** (`gemini-2.5-flash`) vs **Groq** (`llama-3.1-8b-instant`).

---

## Document: sample1.txt

| Metric / Output | Gemini (`gemini-2.5-flash`) | Groq (`llama-3.1-8b-instant`) |
| :--- | :--- | :--- |
| **Summary** | Concise summary of sample 1... | Alternative summary of sample 1... |
| **Accuracy Score** | 5/5 | 5/5 |
| **Coverage Score** | 5/5 | 4/5 |
| **Justification** | Captured all main points without hallucinations. | Missed minor sub-point regarding timelines. |
Configuration & Customization
Inside app.py, you can modify model identifiers directly:

Python
# Active Model Endpoints
GEMINI_PRIMARY_MODEL = "gemini-2.5-flash"
GEMINI_FALLBACK_MODEL = "gemini-2.5-flash-lite"
GROQ_MODEL = "llama-3.1-8b-instant"
License
MIT License. See LICENSE file for details.