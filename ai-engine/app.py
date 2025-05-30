from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import json
import demjson3
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
# @lru_cache(maxsize=100)
# def get_cached_test_cases(endpoint: str):
#     return generate_test_cases_internal(endpoint)


def generate_test_cases_internal(endpoint: str, category: str = None, max_retries=3, min_cases=5):
    # More explicit prompt for LLM
    if category:
        prompt = f"""
You are an expert API test case generator.

Your task is to generate a diverse and realistic set of API test cases for the given endpoint: **{endpoint}**.

**IMPORTANT:** Every test case MUST have a non-empty, meaningful description. If you do not include a unique, meaningful description for each test case, your output will be rejected.

Return ONLY a valid JSON array of {category} test cases. Each test case must be a JSON object with the following fields (in this order):
- description (string)  # Short, unique, and meaningful description of what this test case checks and how it is different
- request_url (string)
- http_method (string)
- request_body (object or N/A)
- expected_response_code (number)
- expected_response_body (object)

## Requirements:
- Generate at least 5 varied {category} test cases.
- Ensure variety in HTTP methods, request bodies, and expected responses.
- Use realistic and meaningful values based on typical API usage.
- **Every test case must have a unique and concise description explaining its purpose or what makes it different.**

## Guidelines:
- Positive tests: successful and valid use cases.
- Negative tests: invalid inputs, missing parameters, wrong HTTP methods, etc.
- Edge tests: boundary conditions (very long strings, empty values, special characters, large numbers, etc.)
- Security tests: XSS, SQL injection, invalid tokens, unauthorized access attempts.

## Output format example:
[
  {{
    "description": "Valid GET request for resource 1. Checks normal retrieval.",
    "request_url": "https://api.example.com/resource/1",
    "http_method": "GET",
    "request_body": {{}},
    "expected_response_code": 200,
    "expected_response_body": {{"id": 1, "name": "foo"}}
  }}
]

## Important:
- Do NOT include any explanation or text outside the JSON.
- Do NOT repeat the same test cases or values.
- Use double quotes for all keys and string values.
- Do not include any explanatory text or markdown - ONLY valid JSON.
- Properly escape any special characters in strings.
- Use proper JSON syntax for nested objects and arrays.
- Ensure all objects and arrays have matching closing brackets/braces.
- Do not include any tokens, formatting markers, or internal model tokens.
- **Do NOT truncate your output. Always finish the JSON array completely, including all closing brackets and commas.**
- If you reach the end of your output, always close all open objects and arrays so the JSON is valid and complete.

Now generate a complete, unique, diverse set of {category} test cases for **{endpoint}** in the format above.
"""
    else:
        prompt = f"""
You are an expert API test case generator.

Your task is to generate a diverse and realistic set of API test cases for the given endpoint: **{endpoint}**.

**IMPORTANT:** Every test case MUST have a non-empty, meaningful description. If you do not include a unique, meaningful description for each test case, your output will be rejected.

Return ONLY a valid JSON object with the following structure:
{{
  "positive_tests": [{{...}}],
  "negative_tests": [{{...}}],
  "edge_tests": [{{...}}],
  "security_tests": [{{...}}]
}}

## Requirements:
- Each array must contain at least **{min_cases} varied test cases**.
- Ensure variety in:
  - HTTP methods (GET, POST, PUT, DELETE, PATCH where appropriate)
  - Request bodies (with different key-value combinations, data types, and optional/missing fields)
  - Expected response codes and bodies
- Use realistic and meaningful values based on typical API usage.
- **Every test case must have a unique and concise description explaining its purpose or what makes it different.**

## Guidelines:
- Positive tests should validate successful and valid use cases.
- Negative tests should cover invalid inputs, missing parameters, wrong HTTP methods, etc.
- Edge tests should check boundary conditions (very long strings, empty values, special characters, large numbers, etc.)
- Security tests should cover cases like XSS, SQL injection, invalid tokens, unauthorized access attempts.

## Output format example:
{{
  "positive_tests": [
    {{
      "description": "Valid GET request for resource 1. Checks normal retrieval.",
      "request_url": "string",
      "http_method": "string",
      "request_body": {{ key-value pairs }},
      "expected_response_code": number,
      "expected_response_body": {{ key-value pairs }}
    }}
  ],
  "negative_tests": [{{...}}],
  "edge_tests": [{{...}}],
  "security_tests": [{{...}}]
}}

## Important:
- Do NOT include any explanation or text outside the JSON.
- Do NOT repeat the same test cases or values.
- Avoid code-like expressions (like 'a'*100). Instead, use actual long strings.
- Focus on making these test cases practical for a real-world API.
- Use double quotes for all keys and string values
- Do not use single quotes around URLs
- Do not include any explanatory text or markdown - ONLY valid JSON
- Properly escape any special characters in strings
- Use proper JSON syntax for nested objects and arrays
- Ensure all objects and arrays have matching closing brackets/braces
- Do not include any tokens, formatting markers, or internal model tokens
- **Do NOT truncate your output. Always finish the JSON object completely, including all closing brackets and commas.**
- If you reach the end of your output, always close all open objects and arrays so the JSON is valid and complete.

Now generate a complete, unique, diverse set of test cases for **{endpoint}** in the format above.
"""

    for attempt in range(max_retries):
        try:
            print(f"\nGenerating test cases for: {endpoint} (Attempt {attempt + 1})")
            start_time = time.time()
            response = requests.post(
                "http://host.docker.internal:11434/api/generate",
                json={
                    "model": "deepseek-coder:6.7b-instruct",
                    "prompt": prompt,
                    "system": "You are a JSON generator. Only output valid JSON objects. If the user input or your output is not valid JSON, fix it and return valid JSON only. Always parse and repair any malformed JSON in your output before returning.",
                    "stream": False,
                    "options": {
                        "num_predict": 2048,  # Increased from 1024 to 2048
                        "temperature": 0.1,
                        "top_p": 0.8,
                        "stop": ["\n\n", "\n}\n}"]  # Adjusted to avoid stopping inside nested objects
                    }
                },
                timeout=60
            )
            if response.status_code != 200:
                print(f"Ollama API error: {response.text}")
                continue
            result = response.json()
            raw_response = result.get("response", "").strip()
            print(f"\nRaw response from Ollama (Attempt {attempt+1}):\n{raw_response}")
            # Accept both array and object as valid JSON root
            if not raw_response or (not raw_response.strip().startswith('{') and not raw_response.strip().startswith('[')):
                print(f"No JSON found in response (Attempt {attempt+1}). Retrying...")
                continue
            # Strictly extract only the first valid JSON object or array
            start_obj = raw_response.find('{')
            start_arr = raw_response.find('[')
            if (start_obj == -1 and start_arr == -1):
                print(f"No JSON object or array found in response (Attempt {attempt+1}). Retrying...")
                continue
            if start_arr != -1 and (start_obj == -1 or start_arr < start_obj):
                # Array comes first
                start = start_arr
                end = raw_response.rfind(']') + 1
            else:
                # Object comes first
                start = start_obj
                end = raw_response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = raw_response[start:end]
                # Remove any trailing commas before closing braces/brackets
                json_str = re.sub(r',([\s\n]*[}}\]])', r'\1', json_str)
                # Remove any data after the last closing brace/bracket
                if json_str.strip().startswith('['):
                    json_str = json_str[:json_str.rfind(']')+1]
                else:
                    json_str = json_str[:json_str.rfind('}')+1]
                try:
                    parsed = json.loads(json_str)
                    # If the response is a dict with a single key (e.g., 'positive_tests'), extract the array
                    if isinstance(parsed, dict) and len(parsed) == 1:
                        key = next(iter(parsed))
                        if key in ["positive_tests", "negative_tests", "edge_tests", "security_tests"] and isinstance(parsed[key], list):
                            arr = parsed[key]
                            if category:
                                arr = filter_by_category(arr, category)
                            return arr
                    # If the response is already an array, filter by category if needed
                    if isinstance(parsed, list):
                        arr = parsed
                        if category:
                            arr = filter_by_category(arr, category)
                        return arr
                    # Fallback: return the parsed object
                    return parsed
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
            else:
                print(f"No JSON object or array found in response (Attempt {attempt+1}). Retrying...")
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

def generate_n_test_cases(endpoint: str, category: str, n: int = 5, max_retries=3):
    test_cases = []
    required_keys = [
        "request_url",
        "http_method",
        "headers",
        # "content_type",  # Removed content_type from required keys
        "request_body",
        "expected_response_code",
        "expected_response_body",
        "description"  # Add description to required keys
    ]
    def normalize_test_case(tc):
        # If the test case is not a dict, return a dict with all N/A
        if not isinstance(tc, dict):
            return {k: "N/A" for k in required_keys}
        # If it already has the required keys, return as is
        if all(k in tc for k in required_keys):
            return tc
        # Try to map common LLM keys to expected keys
        mapping = {
            "url": "request_url",
            "method": "http_method",
            "status": "expected_response_code",
            "data": "expected_response_body",
            "body": "request_body",
            "response_code": "expected_response_code",
            "response_body": "expected_response_body",
            "desc": "description"
        }
        norm = {k: tc.get(k, "N/A") for k in required_keys}
        for src, dst in mapping.items():
            if src in tc and norm[dst] == "N/A":
                norm[dst] = tc[src]
        # If the LLM returned a nested 'data' or 'body', use as response/request body
        if "data" in tc and norm["expected_response_body"] == "N/A":
            norm["expected_response_body"] = tc["data"]
        if "body" in tc and norm["request_body"] == "N/A":
            norm["request_body"] = tc["body"]
        # If the LLM returned a 'desc' or similar, use as description
        if "desc" in tc and norm["description"] == "N/A":
            norm["description"] = tc["desc"]
        return norm


    def clean_and_parse_json(raw_response):
        # Try to extract the first valid JSON object
        start = raw_response.find('{')
        end = raw_response.rfind('}') + 1
        if start >= 0 and end > start:
            json_str = raw_response[start:end]
            # Remove any trailing commas before closing braces/brackets
            json_str = re.sub(r',([\s\n]*[}}\]])', r'\1', json_str)
            # Remove any data after the last closing brace
            json_str = json_str[:json_str.rfind('}')+1]
            try:
                return json.loads(json_str)
            except Exception as e:
                print(f"Failed to parse JSON: {e}\nRaw: {json_str}")
                return None
        else:
            print(f"No JSON object found in response. Raw: {raw_response}")
            return None

    for i in range(n):
        single_prompt = f"""
API Endpoint: {endpoint}

Generate one {category} test case for this API endpoint.
Return ONLY a valid JSON object for the test case, with ALL of these fields:
- request_url (string)
- http_method (string)
- headers (object or N/A)
- content_type (string or N/A)
- request_body (object or N/A)
- expected_response_code (number or string)
- expected_response_body (object or string)

Example:
{{
  "request_url": "https://api.example.com/resource/1",
  "http_method": "GET",
  "headers": {{"Authorization": "Bearer token"}},
  "content_type": "application/json",
  "request_body": {{}},
  "expected_response_code": 200,
  "expected_response_body": {{"id": 1, "name": "foo"}}
}}

Do not include any explanation, markdown, or extra text. Only output the JSON object.
"""
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    "http://host.docker.internal:11434/api/generate",
                    json={
                        "model": "deepseek-coder:6.7b-instruct",
                        "prompt": single_prompt,
                        "system": "You are a JSON generator. Only output valid JSON objects. If the user input or your output is not valid JSON, fix it and return valid JSON only. Always parse and repair any malformed JSON in your output before returning.",
                        "stream": False,
                        "options": {
                            "num_predict": 4096,  # Increased for more complete output
                            "temperature": 0.1,
                            "top_p": 0.8
                            # No 'stop' parameter to avoid truncation
                        }
                    },
                    timeout=60
                )
                if response.status_code != 200:
                    print(f"Ollama API error: {response.text}")
                    continue
                result = response.json()
                raw_response = result.get("response", "").strip()
                print(f"\nRaw response from Ollama (Test {i+1}, Attempt {attempt+1}):\n{raw_response}")
                test_case = clean_and_parse_json(raw_response)
                if test_case:
                    norm = normalize_test_case(test_case)
                    # Fallback: if most fields are N/A, add a message
                    na_count = sum(1 for v in norm.values() if v == "N/A")
                    if na_count >= 5:
                        norm["expected_response_body"] = f"LLM did not return a valid {category} test case. Raw: {raw_response[:200]}..."
                    test_cases.append(norm)
                    break
                else:
                    print(f"Failed to parse test case (Test {i+1}, Attempt {attempt+1})")
            except Exception as e:
                print(f"Exception during LLM call (Test {i+1}, Attempt {attempt+1}): {e}")
                continue
    return test_cases

def filter_by_category(testcases, category):
    """
    Filters a list of test cases to only include those matching the given category in their description or metadata.
    If the input is already a list of only the selected category, returns as is.
    """
    # Accept both full category name and short (e.g., 'positive' or 'positive_tests')
    cat = category.lower()
    filtered = []
    for tc in testcases:
        # Some LLMs add a 'category' field, some only have description
        tc_cat = tc.get('category', '').lower() if isinstance(tc, dict) else ''
        desc = tc.get('description', '').lower() if isinstance(tc, dict) else ''
        if cat in tc_cat or cat in desc:
            filtered.append(tc)
    # If nothing matched, assume all are of the requested category (LLM may not label)
    if not filtered and isinstance(testcases, list):
        filtered = testcases
    # Always return at least 5 (truncate or pad with N/A if needed)
    if len(filtered) > 5:
        filtered = filtered[:5]
    elif len(filtered) < 5:
        # Pad with dummy test cases if not enough
        for _ in range(5 - len(filtered)):
            filtered.append({
                "description": f"Dummy {category} test case (insufficient generated)",
                "request_url": "N/A",
                "http_method": "N/A",
                "request_body": {},
                "expected_response_code": 0,
                "expected_response_body": {}
            })
    return filtered

@app.post("/generate-testcases")
async def generate_testcases(request: TestCaseRequest):
    try:
        print(f"\n[DEBUG] Received prompt: {request.prompt}")
        # Expect prompt to be: "<endpoint>\n<category>"
        prompt_lines = request.prompt.split('\n')
        endpoint = prompt_lines[0].strip()
        print(f"[DEBUG] Parsed endpoint: {endpoint}")
        # Try to infer category from prompt
        category = None
        for cat in ["positive", "negative", "edge", "security"]:
            if cat in request.prompt.lower():
                category = cat
                break
        print(f"[DEBUG] Inferred category: {category}")
        if not category:
            # No category specified, generate all categories at once
            test_cases = generate_test_cases_internal(endpoint, min_cases=5)
            print(f"[DEBUG] Generated test cases: {test_cases}")
            if not test_cases or not any(isinstance(test_cases.get(cat+"_tests", []), list) and len(test_cases.get(cat+"_tests", [])) > 0 for cat in ["positive", "negative", "edge", "security"]):
                return {
                    "testcases": json.dumps([]),
                    "error": f"No test cases generated for endpoint: {endpoint}"
                }
            return {
                "testcases": json.dumps(test_cases, ensure_ascii=False)
            }
        else:
            # Category specified, generate only that category, and ensure at least 5 test cases
            test_cases = generate_test_cases_internal(endpoint, category, min_cases=5)
            print(f"[DEBUG] Generated test cases: {test_cases}")
            if not test_cases or (isinstance(test_cases, list) and len(test_cases) == 0):
                return {
                    "testcases": json.dumps([]),
                    "error": f"No test cases generated for endpoint: {endpoint} and category: {category}"
                }
            # Only return the selected category's test cases in the expected structure
            result = {cat+"_tests": [] for cat in ["positive", "negative", "edge", "security"]}
            result[category+"_tests"] = test_cases
            return {
                "testcases": json.dumps(result, ensure_ascii=False)
            }
    except Exception as e:
        print(f"\n[ERROR] in generate_testcases endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

