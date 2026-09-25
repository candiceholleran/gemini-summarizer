import csv
import json
import os
import re
from pathlib import Path
from google import genai
from google.genai.errors import APIError, ServerError
from groq import Groq, GroqError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# 1. Configuration
INPUT_DIR = Path("./documents")
OUTPUT_MD = Path("batch_summary_results.md")
CSV_LOG = Path("eval_results.csv")

# Model Endpoints
GEMINI_PRIMARY_MODEL = "gemini-2.5-flash"
GEMINI_FALLBACK_MODEL = "gemini-2.5-flash-lite"
GROQ_MODEL = "llama-3.1-8b-instant"

# Initialize Clients
gemini_client = genai.Client()
groq_client = Groq()


# 2. Resilient API Call Wrappers
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=3, max=10),
    retry=retry_if_exception_type((ServerError, APIError)),
    reraise=True,
)
def _execute_gemini_request(model_name: str, prompt_text: str) -> str:
    response = gemini_client.models.generate_content(
        model=model_name,
        contents=prompt_text,
        config={"tools": []},  # Explicitly silences Automatic Function Calling (AFC) warning
    )
    return response.text


def call_gemini(prompt_text: str) -> str:
    """Attempts primary Gemini model, falling back to secondary endpoint if 503 capacity errors persist."""
    try:
        return _execute_gemini_request(GEMINI_PRIMARY_MODEL, prompt_text)
    except (ServerError, APIError) as primary_err:
        print(f"    ⚠️ Primary model ({GEMINI_PRIMARY_MODEL}) unavailable. Falling back to {GEMINI_FALLBACK_MODEL}...")
        try:
            return _execute_gemini_request(GEMINI_FALLBACK_MODEL, prompt_text)
        except Exception as fallback_err:
            raise RuntimeError(f"Both Gemini primary and fallback models failed: {fallback_err}") from primary_err


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(GroqError),
    reraise=True,
)
def call_groq(prompt_text: str) -> str:
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt_text}],
        model=GROQ_MODEL,
    )
    return response.choices[0].message.content


# 3. Quality Evaluation Pass (LLM-as-a-Judge)
def evaluate_summary(original_text: str, summary: str) -> dict:
    eval_prompt = f"""
You are an expert AI evaluator. Assess the following summary against the original document.

Original Document:
\"\"\"
{original_text}
\"\"\"

Generated Summary:
\"\"\"
{summary}
\"\"\"

Grade the summary on two metrics:
1. Accuracy (1-5): Does the summary contain factual errors or hallucinations absent from the source?
2. Coverage (1-5): Does the summary capture the main key points of the original document?

Respond ONLY with a valid JSON object matching this exact structure:
{{
  "accuracy_score": <int 1-5>,
  "coverage_score": <int 1-5>,
  "justification": "<one-line sentence explaining the scores>"
}}
"""
    try:
        response_text = call_gemini(eval_prompt)
        cleaned_json = re.sub(r"^```json\s*|\s*```$", "", response_text.strip())
        eval_data = json.loads(cleaned_json)
        return {
            "accuracy_score": int(eval_data.get("accuracy_score", 0)),
            "coverage_score": int(eval_data.get("coverage_score", 0)),
            "justification": str(eval_data.get("justification", "N/A")),
        }
    except Exception as e:
        return {
            "accuracy_score": 0,
            "coverage_score": 0,
            "justification": f"Evaluation failed: {e}",
        }


# 4. Batch Comparative Execution Pipeline
def process_and_compare_batch(input_folder: Path, output_md: Path, csv_log: Path):
    if not input_folder.exists() or not input_folder.is_dir():
        print(f"Directory '{input_folder}' does not exist. Creating it now...")
        input_folder.mkdir(parents=True, exist_ok=True)
        print(f"Please place your .txt files inside '{input_folder}' and re-run.")
        return

    txt_files = list(input_folder.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in '{input_folder}'.")
        return

    print(f"Found {len(txt_files)} file(s) for multi-model comparison.\n")

    # Initialize Markdown File
    with open(output_md, "w", encoding="utf-8") as out_f:
        out_f.write(f"# Multi-Model Comparative Summarization Report\n\n")
        out_f.write(f"Comparing **Gemini** (`{GEMINI_PRIMARY_MODEL}`) vs **Groq** (`{GROQ_MODEL}`).\n\n---\n\n")

    # Initialize CSV Log File
    with open(csv_log, "w", newline="", encoding="utf-8") as csv_f:
        writer = csv.writer(csv_f)
        writer.writerow([
            "Filename",
            "Gemini_Accuracy",
            "Gemini_Coverage",
            "Gemini_Justification",
            "Groq_Accuracy",
            "Groq_Coverage",
            "Groq_Justification"
        ])

    for index, file_path in enumerate(txt_files, start=1):
        filename = file_path.name
        print(f"[{index}/{len(txt_files)}] Processing: {filename}...")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()

            if not text_content.strip():
                print(f"  └─ Skipped (File is empty)")
                continue

            prompt = f"Please provide a concise summary of the following document:\n\n{text_content}"

            # Gemini Pass
            print(f"  ├─ Generating Gemini summary...")
            gemini_sum = call_gemini(prompt)
            print(f"  ├─ Evaluating Gemini summary...")
            gemini_eval = evaluate_summary(text_content, gemini_sum)

            # Groq Pass
            print(f"  ├─ Generating Groq summary...")
            groq_sum = call_groq(prompt)
            print(f"  ├─ Evaluating Groq summary...")
            groq_eval = evaluate_summary(text_content, groq_sum)

            print(f"  └─ Complete! Gemini: {gemini_eval['accuracy_score']}/{gemini_eval['coverage_score']} | Groq: {groq_eval['accuracy_score']}/{groq_eval['coverage_score']}")

        except Exception as e:
            print(f"  └─ Failed processing {filename}: {e}")
            continue

        formatted_gemini_sum = gemini_sum.replace('\n', '<br>')
        formatted_groq_sum = groq_sum.replace('\n', '<br>')

        # Append Markdown Comparison
        with open(output_md, "a", encoding="utf-8") as out_f:
            out_f.write(f"## Document: {filename}\n\n")
            out_f.write(f"| Metric / Output | Gemini (`{GEMINI_PRIMARY_MODEL}`) | Groq (`{GROQ_MODEL}`) |\n")
            out_f.write(f"| :--- | :--- | :--- |\n")
            out_f.write(f"| **Summary** | {formatted_gemini_sum} | {formatted_groq_sum} |\n")
            out_f.write(f"| **Accuracy Score** | {gemini_eval['accuracy_score']}/5 | {groq_eval['accuracy_score']}/5 |\n")
            out_f.write(f"| **Coverage Score** | {gemini_eval['coverage_score']}/5 | {groq_eval['coverage_score']}/5 |\n")
            out_f.write(f"| **Justification** | {gemini_eval['justification']} | {groq_eval['justification']} |\n\n")
            out_f.write("---\n\n")

        # Append CSV Metrics
        with open(csv_log, "a", newline="", encoding="utf-8") as csv_f:
            writer = csv.writer(csv_f)
            writer.writerow([
                filename,
                gemini_eval["accuracy_score"],
                gemini_eval["coverage_score"],
                gemini_eval["justification"],
                groq_eval["accuracy_score"],
                groq_eval["coverage_score"],
                groq_eval["justification"]
            ])

    print(f"\nComparative batch pipeline complete!")
    print(f"  ├─ Markdown report: '{output_md}'")
    print(f"  └─ CSV metrics log: '{csv_log}'")


if __name__ == "__main__":
    process_and_compare_batch(INPUT_DIR, OUTPUT_MD, CSV_LOG)