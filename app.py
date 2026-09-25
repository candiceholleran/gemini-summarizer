from google import genai
from google.genai.errors import APIError, ServerError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# 1. Initialize the client (reads GEMINI_API_KEY from environment)
client = genai.Client()

# 2. Read local text file
file_path = "sample.txt"

with open(file_path, "r", encoding="utf-8") as file:
    text_content = file.read()

prompt = f"Please summarize the following text:\n\n{text_content}"


# 3. Define API call with retry logic
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ServerError, APIError)),
    reraise=True,
)
def call_gemini_with_retry(prompt_text: str):
    print("Sending request to Gemini API...")
    return client.models.generate_content(
        model="gemini-3.6-flash",  #gemini-2.5-flash
        contents=prompt_text,
    )


# 4. Execute and print output
try:
    response = call_gemini_with_retry(prompt)
    print("\n--- Summary Output ---")
    print(response.text)
except Exception as e:
    print(f"\nFailed after retries: {e}")