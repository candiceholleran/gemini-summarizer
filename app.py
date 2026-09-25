import os
from pathlib import Path
from google import genai
from google.genai.errors import APIError, ServerError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# 1. Configuration
INPUT_DIR = Path("./documents")
OUTPUT_FILE = Path("batch_summary_results.md")
MODEL_NAME = "gemini-3.5-flash-lite"

# Initialize client (reads GEMINI_API_KEY from environment)
client = genai.Client()


# 2. Resilient API Call Function
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


# 3. Batch Processor Function
def process_text_files(input_folder: Path, output_md: Path):
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

    # Initialize or overwrite the output markdown document
    with open(output_md, "w", encoding="utf-8") as out_f:
        out_f.write("# Batch Document Summaries\n\n")

    for index, file_path in enumerate(txt_files, start=1):
        filename = file_path.name
        print(f"[{index}/{len(txt_files)}] Processing: {filename}...")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()

            if not text_content.strip():
                print(f"  └─ Skipped (File is empty)")
                summary_content = "*[Skipped: File was empty]*"
            else:
                prompt = f"Please provide a concise summary of the following document:\n\n{text_content}"
                response = call_gemini_with_retry(prompt)
                summary_content = response.text
                print(f"  └─ Success")

        except Exception as e:
            # Catch file IO errors or persistent API failures so execution continues
            print(f"  └─ Failed to process {filename}: {e}")
            summary_content = f"**Error processing file**: `{e}`"

        # Append formatted result to the single output markdown file
        with open(output_md, "a", encoding="utf-8") as out_f:
            out_f.write(f"## Document: {filename}\n\n")
            out_f.write(f"{summary_content}\n\n")
            out_f.write("---\n\n")

    print(f"\nBatch processing complete! Output saved to '{output_md}'.")


if __name__ == "__main__":
    process_text_files(INPUT_DIR, OUTPUT_FILE)