
**Summary Diagram**

User (Frontend) -->  POST /generate-testcases  (Backend) -->  generate_test_cases_internal() (AI Engine) -->  POST /api/generate (Ollama LLM) -->  LLM Response → Clean/Parse → Return Test Cases --> Backend → Frontend → Display to User

**Sample Output**

<img width="1728" alt="Screenshot 2025-05-18 at 17 31 57" src="https://github.com/user-attachments/assets/f2bc0e00-2d23-4b6a-a8b3-1699b27ff723" />
