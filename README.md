
Summary Diagram

User (Frontend) -->  POST /generate-testcases  (Backend) -->  generate_test_cases_internal() (AI Engine) -->  POST /api/generate (Ollama LLM) -->  LLM Response → Clean/Parse → Return Test Cases --> Backend → Frontend → Display to User
