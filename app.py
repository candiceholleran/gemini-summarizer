import csv
import json
import os
import re
from pathlib import Path
from google import genai
from google.genai.errors import APIError, ServerError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# 1. Configuration
INPUT_DIR = Path("./documents")
OUTPUT_MD = Path("batch_summary_results.md")
CSV_LOG = Path("eval_results.csv")
MODEL_NAME = "gemini-3.5-flash-lite"

# Initialize client (reads GEMINI_API_KEY from environment)
client = genai.Client()


# 2. Resilient API Call Wrapper
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ServerError, APIError)),
    reraise=True,
)
def call_gemini_with_retry(prompt_text: str):
    return client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt_text,
    )


# 3. LLM-as-a-Judge Evaluation Function
def evaluate_summary(original_text: str, summary: str) -> dict:
    eval_prompt = f"""
You are an expert AI evaluator. Assess the following generated summary against the original document.

Original Document:
\"\"\"
{original_text}
\"\"\"

Generated Summary:
\"\"\"
{summary}
\"\"\"

Grade the summary on two metrics:
1. Accuracy (1-5): Does the summary contain factual errors or hallucinations absent from the original source?
2. Coverage (1-5): Does the summary capture the main key points of the original document?

Respond ONLY with a valid JSON object matching this exact structure:
{{
  "accuracy_score": <int 1-5>,
  "coverage_score": <int 1-5>,
  "justification": "<one-line sentence explaining the scores>"
}}
"""
    try:
        response = call_gemini_with_retry(eval_prompt)
        # Clean JSON markdown formatting wrappers if returned by the model
        cleaned_json = re.sub(r"^```json\s*|\s*```$", "", response.text.strip())
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


# 4. Batch Processor & Evaluator
def process_and_evaluate_batch(input_folder: Path, output_md: Path, csv_log: Path):
    if not input_folder.exists() or not input_folder.is_dir():
        print(f"Directory '{input_folder}' does not exist. Creating it now...")
        input_folder.mkdir(parents=True, exist_ok=True)
        print(f"Please place your .txt files inside '{input_folder}' and re-run.")
        return

    txt_files = list(input_folder.glob("*.txt"))

    if not txt_files:
        print(f"No .txt files found in '{input_folder}'.")
        return

    print(f"Found {len(txt_files)} file(s) to process.\n")

    # Initialize Markdown File
    with open(output_md, "w", encoding="utf-8") as out_f:
        out_f.write("# Batch Document Summaries with Quality Evaluation\n\n")

    # Initialize CSV Log File with Headers
    with open(csv_log, "w", newline="", encoding="utf-8") as csv_f:
        writer = csv.writer(csv_f)
        writer.writerow(["Filename", "Accuracy Score (1-5)", "Coverage Score (1-5)", "Justification"])

    for index, file_path in enumerate(txt_files, start=1):
        filename = file_path.name
        print(f"[{index}/{len(txt_files)}] Processing: {filename}...")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()

            if not text_content.strip():
                print(f"  └─ Skipped (File is empty)")
                summary_content = "*[Skipped: File was empty]*"
                eval_results = {"accuracy_score": 0, "coverage_score": 0, "justification": "Skipped: File was empty"}
            else:
                # Pass 1: Summarize
                sum_prompt = f"Please provide a concise summary of the following document:\n\n{text_content}"
                sum_response = call_gemini_with_retry(sum_prompt)
                summary_content = sum_response.text
                print(f"  └─ Generated summary successfully")

                # Pass 2: Evaluate (LLM-as-a-Judge)
                print(f"  └─ Running evaluation judge pass...")
                eval_results = evaluate_summary(text_content, summary_content)
                print(f"  └─ Eval complete: Accuracy={eval_results['accuracy_score']}/5, Coverage={eval_results['coverage_score']}/5")

        except Exception as e:
            print(f"  └─ Failed processing {filename}: {e}")
            summary_content = f"**Error processing file**: `{e}`"
            eval_results = {"accuracy_score": 0, "coverage_score": 0, "justification": f"Execution error: {e}"}

        # Append to Markdown output
        with open(output_md, "a", encoding="utf-8") as out_f:
            out_f.write(f"## Document: {filename}\n\n")
            out_f.write(f"### Summary\n{summary_content}\n\n")
            out_f.write(f"### Quality Evaluation (LLM-as-a-Judge)\n")
            out_f.write(f"- **Accuracy Score**: {eval_results['accuracy_score']}/5\n")
            out_f.write(f"- **Coverage Score**: {eval_results['coverage_score']}/5\n")
            out_f.write(f"- **Justification**: {eval_results['justification']}\n\n")
            out_f.write("---\n\n")

        # Append to CSV log file
        with open(csv_log, "a", newline="", encoding="utf-8") as csv_f:
            writer = csv.writer(csv_f)
            writer.writerow([
                filename,
                eval_results["accuracy_score"],
                eval_results["coverage_score"],
                eval_results["justification"]
            ])

    print(f"\nBatch pipeline complete!")
    print(f"  ├─ Summaries and scores saved to '{output_md}'")
    print(f"  └─ Evaluation log exported to '{csv_log}'")


if __name__ == "__main__":
    process_and_evaluate_batch(INPUT_DIR, OUTPUT_MD, CSV_LOG)