# 🌾 AI-Based Farmer Query Support and Advisory System (Kisan Mitra AI)

A robust, full-stack, college-grade agricultural advisory application designed to empower farmers with real-time, actionable agronomic advice. Built with a **Python Flask** backend, an accessible **HTML5 / CSS3 / Vanilla JavaScript** frontend, and a self-contained **SQLite** database.

---

## 🌟 Key Features

1. **User Registration & Secure Authentication**:
   - Secure farmer accounts with salted cryptographic password hashing (`scrypt` via `werkzeug.security`).
   - Tamper-proof HTTP-only signed session cookies.
   - 1-click **Demo Farmer Guest Mode** for fast college presentations and examiner review.

2. **Multimodal Farmer Queries**:
   - **Text Queries**: Ask questions in English, Hindi, or Hinglish regarding crop diseases, soil nutrients, fertilizers, and irrigation.
   - **Image Upload & Crop Diagnosis**: Upload photographs of diseased crop leaves (PNG, JPG, WEBP). Validated via Pillow image header inspection and stored with randomized safe filenames.
   - **Voice Input (Speech-to-Text)**: Hands-free voice queries using the browser's native Web Speech API (`SpeechRecognition`).
   - **Spoken Audio Responses (Text-to-Speech)**: One-click "Listen" audio button on every advisory response using `window.speechSynthesis`.

3. **Weather Information & Agro-Advisories**:
   - Integrated with the OpenWeatherMap API server-side (keeping API keys safe from the browser).
   - Dynamically analyzes temperature, humidity, and wind speed to deliver practical farming tips (e.g., delaying foliar spraying during high winds or rain).
   - **Resilient Fallback Mode**: If no API key is provided or the network is offline, automatically activates a realistic **Simulated / Demo Mode** clearly badged in the UI.

4. **Configurable AI Advisory Engine**:
   - Supports **Google Gemini** (`gemini-2.5-flash`, `gemini-1.5-flash`) and **OpenAI** (`gpt-4o-mini`) via environment variables.
   - Multimodal image reasoning sends plant photos directly to vision-capable AI models.
   - **Offline Knowledge Engine**: When external API keys are not supplied, an intelligent rule-based agricultural engine answers questions on solanaceous crops (tomato/potato), wheat, rice/paddy, pest management, and fertilizers.

5. **Conversation History for Each User**:
   - Every consultation thread is saved to SQLite linked to the farmer's account.
   - Seamlessly switch between past conversations or start new consultations.
   - Cascade deletion support when a conversation is deleted.

6. **Responsible AI & Agricultural Safety**:
   - Mandatory non-guarantee disclaimer on the UI and appended to all AI responses:
     > *"⚠️ Agricultural Advisory Disclaimer: Recommendations are AI-generated for informational guidance. Soil, climate, and crop varieties differ regionally. Please verify fertilizer and pesticide dosages with your local Krishi Vigyan Kendra (KVK) or Agriculture Officer before field application."*

---

## 🏗️ System Architecture

```
StudentPortfolio/
│
├── backend/
│   ├── __init__.py           # Package initializer
│   ├── config.py             # Loads .env, paths, and security limits
│   ├── database.py           # SQLite schema (Users, Conversations, Messages)
│   ├── auth.py               # User registration, login, scrypt hashing, sessions
│   ├── ai_service.py         # Gemini/OpenAI API caller + offline fallback engine
│   ├── weather_service.py    # OpenWeatherMap client + simulated weather generator
│   └── routes.py             # REST API routes (/api/query, /api/weather, etc.)
│
├── frontend/
│   ├── index.html            # Main farmer dashboard UI
│   ├── login.html            # Authentication portal (Sign In, Register, Demo)
│   ├── css/
│   │   └── style.css         # Agricultural styling, responsive grid & cards
│   └── js/
│       ├── app.js            # Main chat controller & UI rendering
│       ├── auth.js           # Client-side session and auth requests
│       ├── voice.js          # Web Speech API (STT voice input & TTS audio readout)
│       └── weather.js        # Weather fetching and display manager
│
├── uploads/                  # Secure directory for crop photos
├── tests/                    # Automated pytest test suite
│   ├── conftest.py           # Isolated test fixtures
│   ├── test_auth.py          # Registration, login, and password hash tests
│   ├── test_uploads.py       # Image upload & malicious file rejection tests
│   ├── test_api_errors.py    # Error handling, validation & disclaimer tests
│   └── test_conversations.py # Message history and privacy isolation tests
│
├── .env.example              # Template for API keys
├── .env                      # Local environment configuration
├── requirements.txt          # Python dependencies
└── run.py                    # Server startup script
```

---

## 🚀 Setup & Execution Guide

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.13)
- Modern Web Browser (Google Chrome or Microsoft Edge recommended for Web Speech API)

### 2. Install Dependencies
Open PowerShell or your terminal in the project directory and install the required packages:
```powershell
python -m pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` (or modify the existing `.env`):
```ini
SECRET_KEY=your-secret-key-here
AI_PROVIDER=gemini
AI_MODEL_NAME=gemini-2.5-flash
GEMINI_API_KEY=your_gemini_api_key_here
WEATHER_API_KEY=your_openweathermap_api_key_here
DEFAULT_CITY=Delhi,IN
MAX_UPLOAD_SIZE_MB=5
```
> **Note**: Even if you leave `GEMINI_API_KEY` and `WEATHER_API_KEY` blank, the application will automatically run in **Simulated / Offline Demo Mode**, ensuring flawless presentations without API dependencies.

### 4. Start the Application Server
Run the Flask server:
```powershell
python run.py
```
You will see:
```
=======================================================
 🌾 AI-Based Farmer Query Support and Advisory System
 🚀 Server running at: http://127.0.0.1:5000
=======================================================
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

---

## 🧪 Running Automated Tests

A comprehensive test suite with 17 automated tests is included to verify all functionality:
```powershell
python -m pytest tests -v
```

### What the Test Suite Verifies:
- **Authentication**: Registration, password length validation, duplicate username rejection, scrypt password hashing verification, login success/failure, session invalidation on logout.
- **File Upload Security**: Acceptance of valid PNG/JPG/WEBP images, rejection of executable/script files (`.exe`, `.sh`), and rejection of fake disguised images using Pillow header verification.
- **Error Resilience**: Handling of empty queries, rejection of unauthenticated queries, weather fallback responses, 404 on invalid conversations.
- **Data Privacy & Persistence**: Multi-turn conversation persistence and isolation between different users.

---

## 🎓 College Viva & Evaluation FAQ

| Question | Recommended Answer |
| :--- | :--- |
| **Why Flask instead of Django?** | Flask is lightweight and modular, giving full control over the architecture without unnecessary boilerplate. It allows direct demonstration of REST API design, session handling, and database integration. |
| **How are passwords stored securely?** | We use `werkzeug.security.generate_password_hash` with the `scrypt` key derivation function and random salts. Passwords cannot be reverse-engineered even if the database is compromised. |
| **How do you prevent malicious image uploads?** | 1) Whitelist file extensions (`.png`, `.jpg`, `.jpeg`, `.webp`), 2) Validate image headers using Pillow's `Image.verify()`, 3) Sanitize filenames with `secure_filename()` and a random UUID prefix to eliminate directory traversal attacks, 4) Enforce a 5 MB file size limit. |
| **What happens if the external AI or Weather API fails?** | The system includes automated fallback mechanisms: `ai_service.py` falls back to an internal rule-based knowledge engine, and `weather_service.py` provides simulated regional agricultural weather, explicitly flagged with a UI badge. |
| **How does Voice Input & Output work?** | We leverage the browser's standard **Web Speech API**: `SpeechRecognition` handles microphone input and transcribes speech into the textarea, while `SpeechSynthesis` reads out the AI advisory aloud. |
