# Checkpoint 1 for ai-engine/app.py
# Date: 2025-05-21
# This is a backup of the working state of app.py as confirmed by the user.

# --- BEGIN app.py ---
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
    json_str = re.sub(r',(\s*[}}\]])', r'\1', json_str)
    
    return json_str

def generate_test_cases_internal(endpoint: str, max_retries=3):
    # More explicit prompt for LLM
    prompt = f"""
You are an expert API test case generator.

Your task is to generate a diverse and realistic set of 2 API test cases for the given endpoint: **{endpoint}**.

Return ONLY a valid JSON object with the following structure:
{{
  "positive_tests": [{{...}}],
  "negative_tests": [{{...}}],
  "edge_tests": [{{...}}],
  "security_tests": [{{...}}]
}}

## Requirements:
- Each array must contain at least **3 varied test cases**.
- Ensure variety in:
  - HTTP methods (GET, POST, PUT, DELETE, PATCH where appropriate)
  - Request bodies (with different key-value combinations, data types, and optional/missing fields)
  - Expected response codes and bodies
- Use realistic and meaningful values based on typical API usage.

## Guidelines:
- Positive tests should validate successful and valid use cases.
- Negative tests should cover invalid inputs, missing parameters, wrong HTTP methods, etc.
- Edge tests should check boundary conditions (very long strings, empty values, special characters, large numbers, etc.)
- Security tests should cover cases like XSS, SQL injection, invalid tokens, unauthorized access attempts.

## Output format example:
{{
  "positive_tests": [
    {{
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

    def fix_pythonic_strings(raw: str) -> str:
        # Replace "a"*100 with 100 times "a"
        return re.sub(r'"([a-zA-Z0-9])"\s*\*\s*(\d+)', lambda m: '"' + m.group(1) * int(m.group(2)) + '"', raw)

    def remove_incomplete_trailing_objects(json_str: str) -> str:
        """
        Remove incomplete trailing objects from arrays in the JSON string.
        This is a best-effort approach: it looks for the last complete object in each array and trims off any trailing incomplete objects.
        """
        # Remove incomplete objects at the end of arrays (e.g., { ... "rating)
        # This will trim any trailing comma and incomplete object at the end of an array
        # Example: [ {...}, {...}, { ...incomplete... ]  => [ {...}, {...} ]
        def fix_array(arr_match):
            arr = arr_match.group(0)
            # Find all complete objects
            objects = list(re.finditer(r'\{[^\{\}]*\}', arr))
            if not objects:
                return '[]'
            # Find the last complete object
            last_obj = objects[-1]
            # Return array up to the end of the last complete object
            return arr[:last_obj.end()] + ']'  # close the array
        # Apply to all arrays in the JSON
        fixed = re.sub(r'\[.*?\]', fix_array, json_str, flags=re.DOTALL)
        return fixed

    def fix_missing_commas_in_arrays(json_str: str) -> str:
        """
        Insert missing commas between objects in arrays, e.g. [{...}{...}] -> [{...},{...}]
        Only applies inside arrays.
        Handles cases where there are nested braces or tricky content (like quotes inside strings).
        """
        # This regex finds a closing curly brace followed by optional whitespace/newlines and an opening curly brace,
        # but only if the closing brace is not followed by a comma or array/obj end
        # It is robust to nested braces and quoted content
        def replacer(match):
            before = match.group(1)
            between = match.group(2)
            after = match.group(3)
            # Only insert comma if not already present
            if not between.strip().startswith(','):
                return before + ',' + between + after
            return match.group(0)
        # Only operate inside arrays
        # This will match inside [ ... ]
        array_pattern = re.compile(r'(\})(\s*)(\{)', re.MULTILINE)
        return array_pattern.sub(replacer, json_str)

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
            if not raw_response or not raw_response.strip().startswith('{'):
                print(f"No JSON found in response (Attempt {attempt+1}). Retrying...")
                continue
            # Fix pythonic string multiplication before parsing
            fixed_response = fix_pythonic_strings(raw_response)
            # Remove incomplete trailing objects from arrays
            fixed_response = remove_incomplete_trailing_objects(fixed_response)
            # Fix missing commas between objects in arrays (robust)
            fixed_response = fix_missing_commas_in_arrays(fixed_response)
            # Additional fix: Replace nested single quotes in XSS and SQLi test cases
            # Replace title='<script>alert('XSS')</script> with title='<script>alert("XSS")</script>'
            # # Fix SQL injection: ensure closing single quote
            # fixed_response = re.sub(r"title='<script>alert\('XSS'\)</script>'", "title='<script>alert(\\\"XSS\\\")</script>'", fixed_response)
            # # Fix SQL injection: ensure closing single quote
            # fixed_response = re.sub(r"sql='UNION SELECT \* FROM users--(?!')", "sql='UNION SELECT * FROM users--'", fixed_response)
            # Strictly extract only the first valid JSON object (from first { to last })
            start = fixed_response.find('{')
            end = fixed_response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = fixed_response[start:end]
                # Remove any trailing commas before closing braces/brackets
                json_str = re.sub(r',([\s\n]*[}}\]])', r'\1', json_str)
                # Remove any data after the last closing brace
                json_str = json_str[:json_str.rfind('}')+1]
                try:
                    parsed = json.loads(json_str)
                    # If the response is a dict with a single key (e.g., 'positive_tests'), extract the array
                    if isinstance(parsed, dict) and len(parsed) == 1:
                        key = next(iter(parsed))
                        if key in ["positive_tests", "negative_tests", "edge_tests", "security_tests"] and isinstance(parsed[key], list):
                            return parsed[key]
                    # If the response is already an array, return as is
                    if isinstance(parsed, list):
                        return parsed
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
                print(f"No JSON object found in response (Attempt {attempt+1}). Retrying...")
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

def generate_n_test_cases(endpoint: str, category: str, n: int = 3, max_retries=3):
    test_cases = []
    required_keys = [
        "request_url",
        "http_method",
        "headers",
        "content_type",
        "request_body",
        "expected_response_code",
        "expected_response_body"
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
            "response_body": "expected_response_body"
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
        return norm
    def autoclose_json(raw_response):
        # Try to auto-close the last object/array if missing
        s = raw_response.strip()
        # Count braces/brackets
        open_braces = s.count('{')
        close_braces = s.count('}')
        open_brackets = s.count('[')
        close_brackets = s.count(']')
        # Add missing closing braces/brackets
        s += '}' * (open_braces - close_braces)
        s += ']' * (open_brackets - close_brackets)
        return s

    def autoclose_json_brackets(s: str) -> str:
        """
        Attempts to auto-close any unclosed curly braces or square brackets in a JSON string.
        Appends the required number of closing brackets/braces at the end.
        """
        open_curly = s.count('{')
        close_curly = s.count('}')
        open_square = s.count('[')
        close_square = s.count(']')
        s = s.rstrip()
        s += '}' * (open_curly - close_curly)
        s += ']' * (open_square - close_square)
        return s

    def trim_incomplete_object(json_str: str) -> str:
        """
        Trims the last incomplete field or object from a JSON object string.
        This is a best-effort approach: it looks for the last complete key-value pair and trims off any trailing incomplete content.
        """
        last_comma = json_str.rfind(',')
        last_close = max(json_str.rfind('}'), json_str.rfind(']'))
        if last_close > last_comma:
            # Looks like the last object/array is complete
            return json_str[:last_close+1]
        elif last_comma != -1:
            # Trim to the last comma (removes incomplete trailing field)
            return json_str[:last_comma] + '}'
        else:
            # Fallback: just return up to the last closing brace/bracket
            return json_str[:last_close+1] if last_close != -1 else json_str

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
                print(f"Failed to parse JSON: {e}\nRaw: {json_str}\nTrying demjson3 repair...")
                try:
                    repaired = demjson3.decode(json_str)
                    return repaired
                except Exception as e2:
                    print(f"demjson3 repair also failed: {e2}\nRaw: {json_str}")
                    # Try trimming incomplete trailing fields/objects
                    trimmed = trim_incomplete_object(json_str)
                    try:
                        return json.loads(trimmed)
                    except Exception as e3:
                        print(f"trim_incomplete_object also failed: {e3}\nRaw: {trimmed}")
                        # Try autoclose fallback
                        closed = autoclose_json_brackets(json_str)
                        try:
                            return json.loads(closed)
                        except Exception as e4:
                            print(f"autoclose_json_brackets also failed: {e4}\nRaw: {closed}")
                            # Final salvage: try to extract as many top-level fields as possible
                            salvaged = salvage_top_level_fields(json_str)
                            if salvaged:
                                print("salvage_top_level_fields succeeded")
                                return salvaged
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
            category = "positive"
        # Generate 3 test cases by default
        test_cases = generate_n_test_cases(endpoint, category, n=3)
        print(f"[DEBUG] Generated test cases: {test_cases}")
        if not test_cases or (isinstance(test_cases, list) and len(test_cases) == 0):
            return {
                "testcases": json.dumps([]),
                "error": f"No test cases generated for endpoint: {endpoint} and category: {category}"
            }
        return {
            "testcases": json.dumps(test_cases, ensure_ascii=False)
        }
    except Exception as e:
        print(f"\n[ERROR] in generate_testcases endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def salvage_top_level_fields(json_str: str) -> dict:
    """
    Attempts to salvage as many top-level fields as possible from a malformed JSON object string.
    Iteratively removes the last field until parsing succeeds.
    """
    import re
    # Find all top-level key-value pairs
    pairs = list(re.finditer(r'"([^"\\]+)":\s*([\s\S]*?)(?=,\s*"[^"\\]+":|}$)', json_str))
    for i in range(len(pairs), 0, -1):
        try:
            partial = '{' + ','.join(json_str[p.start():p.end()] for p in pairs[:i]) + '}'
            return json.loads(partial)
        except Exception:
            continue
    return {}
# --- END app.py ---
