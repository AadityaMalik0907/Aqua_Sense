# AI Usage and Collaboration Record

This document records the artificial intelligence tooling, prompts, observations, and corrections encountered during the development and testing of the AquaSense project.

---

## 1. AI Tools Used

- **AI Model & Interface**: Google Antigravity powered by **Gemini 3.8 Flash (High)**.
- **Workflow Tools**: Codebase inspection tools (`read_file`, `write_file`, `edit_file`) and terminal command execution (`run_command`, `pytest`).

---

## 2. Actual Prompts Used

### Prompt 1: Front-End Redesign & Welcome Experience
> *"okay go throught the UI files of my project and make some reallyy good looking UI, what I want is that I want you to make a welcome thing or something with aqua sense written on it and then the page comes up not directly the page make sure the UI is good follow some other aesthetic colour scheme and make sure that the UI looks really good and the backend works as it is"*

### Prompt 2: Comprehensive Automated API Testing
> *"Now complete the automated API testing for AquaSense.*
>
> *Use pytest and FastAPI TestClient.*
>
> *Inspect my existing tests before creating new ones.*
>
> *Test these scenarios:*
> 1. *Successful login.*
> 2. *Login with invalid password.*
> 3. *Access device status with valid token.*
> 4. *Access device status with invalid token.*
> 5. *Access device status without a token.*
> 6. *Request a nonexistent device.*
> 7. *Handle an offline device.*
> 8. *Handle malformed device response data.*
> 9. *Handle stale last_seen timestamps.*
> 10. *Validate tank level boundaries:*
>     - *0% should be accepted.*
>     - *100% should be accepted.*
>     - *Values below 0 or above 100 should be rejected.*
>
> *Requirements:*
> - *Tests must be independent.*
> - *Use mock data.*
> - *Do not require an actual IoT device.*
> - *Do not make external API calls.*
> - *Assert both status codes and response bodies.*
> - *Avoid duplicate test cases.*
>
> *Run the entire pytest suite.*
>
> *Fix failures and provide a summary of passed and failed tests.*
> *Do not claim a test passed unless it actually ran successfully."*

---

## 3. Genuine Mistake Made by AI

### The Mistake:
During the initial test suite setup, the AI made two real, unforced errors:
1. **Environment Path Misconfiguration**: When attempting to execute the test suite, the AI ran generic `python -m pytest` and `py -m pytest` commands instead of referencing the project's dedicated virtual environment (`.\.venv\Scripts\python.exe`). Because Python 3.15 is installed under Windows User AppData (`C:\Users\MANISHA MALIK\AppData\Local\Python\...`), this triggered immediate permission and missing package errors (`ResourceUnavailable: The file cannot be accessed by the system` and `No module named pytest`).
2. **Superficial Assertions**: In the earliest test draft, the AI wrote incomplete test cases that only checked `response.status_code == 200` without asserting the response body content (omitting checks for `is_stale`, `status == "online"`, or detailed error payloads).

---

## 4. How the Mistake Was Identified and Corrected

1. **Path Correction**:
   - **Identification**: The terminal output showed command exit code 1 with an OS `ResourceUnavailable` and missing module error on the global launcher.
   - **Correction**: Verified the active virtual environment structure at `d:\AquaSense\.venv`, confirmed `pytest` was installed inside `.venv\Lib\site-packages`, and redirected all test execution commands to explicitly use `.\.venv\Scripts\python.exe -m pytest`.

2. **Assertion Hardening**:
   - **Identification**: Reviewed the test files against the strict requirement to *"Assert both status codes and response bodies"*.
   - **Correction**: Refactored `tests/test_device_status.py`, `tests/test_login.py`, and `tests/test_tank_levels.py` to extract `response.json()` and validate all returned fields:
     - Verified exact error messages (`"detail": "Invalid username or password"`, `"detail": "Bearer token required"`, etc.).
     - Added mock patchers (`unittest.mock.patch`) to simulate corrupt database payloads (non-boolean `online` values and invalid ISO date formats) to test server 500 error boundaries cleanly.
     - Validated tank percentage boundaries (0.0%, 100.0%, -1.0%, 100.5%) at both the API level and Pydantic model level.

