from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import json
from functools import lru_cache
import time
import re

app = FastAPI()

class TestCaseRequest(BaseModel):
    prompt: str

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Cache the test case generation for similar endpoints
@lru_cache(maxsize=100)
def get_cached_test_cases(endpoint: str):
    return generate_test_cases_internal(endpoint)

def clean_json_string(s: str) -> str:
    """Clean and extract valid JSON from the response string."""
    # Find the first { and last }
    start = s.find('{')
    end = s.rfind('}')
    if start == -1 or end == -1:
        return s
    
    # Extract the JSON part
    json_str = s[start:end + 1]
    
    # Remove any trailing commas before closing braces/brackets
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
    
    return json_str

def generate_test_cases_internal(endpoint: str, max_retries=3):
    # More explicit prompt for LLM
    prompt = f"""
You are an API test case generator. Output ONLY a valid JSON object with the following structure and nothing else:
{{
  "positive_tests": [{{...}}],
  "negative_tests": [{{...}}],
  "edge_tests": [{{...}}],
  "security_tests": [{{...}}]
}}
Each array should have at least 2 test cases. Use realistic and diverse values. Example:
{{
  "positive_tests": [
    {{"request_url": "{endpoint}", "http_method": "GET", "headers": {{"Content-Type": "application/json"}}, "content_type": "application/json", "request_body": {{}}, "expected_response_code": 200, "expected_response_body": {{"status": "success"}}}},
    {{"request_url": "{endpoint}", "http_method": "POST", "headers": {{"Content-Type": "application/json"}}, "content_type": "application/json", "request_body": {{"foo": "bar"}}, "expected_response_code": 201, "expected_response_body": {{"id": 1}}}}
  ],
  "negative_tests": [
    {{"request_url": "{endpoint}", "http_method": "POST", "headers": {{}}, "content_type": "application/json", "request_body": {{}}, "expected_response_code": 400, "expected_response_body": {{"error": "Missing header"}}}},
    {{"request_url": "{endpoint}", "http_method": "POST", "headers": {{"Content-Type": "application/json"}}, "content_type": "application/json", "request_body": {{"foo": 123}}, "expected_response_code": 422, "expected_response_body": {{"error": "Invalid type"}}}}
  ],
  "edge_tests": [
    {{"request_url": "{endpoint}", "http_method": "POST", "headers": {{"Content-Type": "application/json"}}, "content_type": "application/json", "request_body": {{"foo": ""}}, "expected_response_code": 400, "expected_response_body": {{"error": "Empty value"}}}},
    {{"request_url": "{endpoint}", "http_method": "POST", "headers": {{"Content-Type": "application/json"}}, "content_type": "application/json", "request_body": {{"foo": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}}, "expected_response_code": 400, "expected_response_body": {{"error": "Too long"}}}}
  ],
  "security_tests": [
    {{"request_url": "{endpoint}", "http_method": "POST", "headers": {{"Content-Type": "application/json"}}, "content_type": "application/json", "request_body": {{"foo": "<script>alert(1)</script>"}}, "expected_response_code": 400, "expected_response_body": {{"error": "XSS detected"}}}},
    {{"request_url": "{endpoint}", "http_method": "POST", "headers": {{"Content-Type": "application/json"}}, "content_type": "application/json", "request_body": {{"foo": "' OR 1=1;--"}}, "expected_response_code": 400, "expected_response_body": {{"error": "SQL injection detected"}}}}
  ]
}}
Do not use code-like expressions such as 'a'*100. Instead, write out the repeated characters explicitly in the JSON.
Now generate real test cases for {endpoint} in this format. Do not add any explanation or text outside the JSON.
"""

    def fix_pythonic_strings(raw: str) -> str:
        # Replace "a"*100 with 100 times "a"
        return re.sub(r'"([a-zA-Z0-9])"\s*\*\s*(\d+)', lambda m: '"' + m.group(1) * int(m.group(2)) + '"', raw)

    for attempt in range(max_retries):
        try:
            print(f"\nGenerating test cases for: {endpoint} (Attempt {attempt + 1})")
            start_time = time.time()
            response = requests.post(
                "http://host.docker.internal:11434/api/generate",
                json={
                    "model": "mistral",
                    "prompt": prompt,
                    "system": "You are a JSON generator. Only output valid JSON objects.",
                    "stream": False,
                    "options": {
                        "num_predict": 1024,
                        "temperature": 0.1,
                        "top_p": 0.8,
                        "stop": ["}\n}", "\n\n"]
                    }
                },
                timeout=40
            )
            if response.status_code != 200:
                print(f"Ollama API error: {response.text}")
                continue
            result = response.json()
            raw_response = result.get("response", "").strip()
            print(f"\nRaw response from Ollama (Attempt {attempt+1}):\n{raw_response}")
            if not raw_response or not raw_response.strip().startswith('{'):
                print(f"No JSON found in response (Attempt {attempt+1}). Retrying...")
                continue
            # Fix pythonic string multiplication before parsing
            fixed_response = fix_pythonic_strings(raw_response)
            # Try to clean and parse the response
            try:
                start = fixed_response.find('{')
                end = fixed_response.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = fixed_response[start:end]
                    json_str = re.sub(r',([\s\n]*[}\]])', r'\1', json_str)
                    test_cases = json.loads(json_str)
                    required_categories = ["positive_tests", "negative_tests", "edge_tests", "security_tests"]
                    for category in required_categories:
                        if category not in test_cases:
                            test_cases[category] = []
                        elif not isinstance(test_cases[category], list):
                            test_cases[category] = []
                    end_time = time.time()
                    test_cases["generation_time"] = f"{end_time - start_time:.2f} seconds"
                    test_cases["attempt"] = attempt + 1
                    return test_cases
                else:
                    raise ValueError("No JSON object found in response")
            except json.JSONDecodeError as e:
                print(f"\nJSON Parse Error (Attempt {attempt + 1}): {e}")
                print(f"Failed to parse JSON at position {e.pos}: {e.msg}")
                if attempt == max_retries - 1:
                    return {
                        "positive_tests": [],
                        "negative_tests": [],
                        "edge_tests": [],
                        "security_tests": [],
                        "error": f"Failed to parse response after {max_retries} attempts",
                        "raw_response": raw_response
                    }
                continue
        except requests.Timeout:
            print(f"\nRequest timed out (Attempt {attempt + 1})")
            if attempt == max_retries - 1:
                return {
                    "positive_tests": [],
                    "negative_tests": [],
                    "edge_tests": [],
                    "security_tests": [],
                    "error": f"Request timed out after {max_retries} attempts"
                }
            continue
        except Exception as e:
            print(f"\nError during test case generation (Attempt {attempt + 1}): {str(e)}")
            if attempt == max_retries - 1:
                return {
                    "positive_tests": [],
                    "negative_tests": [],
                    "edge_tests": [],
                    "security_tests": [],
                    "error": str(e)
                }
            continue
    return {
        "positive_tests": [],
        "negative_tests": [],
        "edge_tests": [],
        "security_tests": [],
        "error": "Failed to generate test cases after all attempts"
    }

@app.post("/generate-testcases")
async def generate_testcases(request: TestCaseRequest):
    try:
        start_time = time.time()
        test_cases = get_cached_test_cases(request.prompt)
        end_time = time.time()
        
        # If there was an error and we have a raw response, include it
        if "error" in test_cases and "raw_response" in test_cases:
            return {
                "testcases": test_cases,
                "processing_time": f"{end_time - start_time:.2f} seconds",
                "raw_response": test_cases["raw_response"]
            }
        
        return {
            "testcases": test_cases,
            "processing_time": f"{end_time - start_time:.2f} seconds"
        }

    except Exception as e:
        print(f"\nError in generate_testcases endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
