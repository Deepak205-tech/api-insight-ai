
**Summary Diagram**

User (Frontend) -->  POST /generate-testcases  (Backend) -->  generate_test_cases_internal() (AI Engine) -->  POST /api/generate (Ollama LLM) -->  LLM Response → Clean/Parse → Return Test Cases --> Backend → Frontend → Display to User

**Sample Output**

<img width="1728" alt="Screenshot 2025-05-24 at 13 44 11" src="https://github.com/user-attachments/assets/edf7cbe2-13ba-46e7-99df-2c552ccd8264" />

