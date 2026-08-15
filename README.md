# 🤖 AI Interview Portal

A complete college-level AI Interview Portal built with **Python + Streamlit + SQLite**.

## Features

- User registration and login
- Password hashing
- Student dashboard
- Technical / HR / Behavioral / Mixed interviews
- Easy / Medium / Hard difficulty
- Dynamic question generation
- Optional OpenAI-powered question generation
- Resume PDF upload and text extraction
- Resume-context interview questions
- Answer evaluation and scoring
- Feedback, strengths and improvement suggestions
- Interview history
- Average and best score dashboard
- SQLite database
- Responsive Streamlit UI

## 1. Create a virtual environment

### Windows

```bash
py -m venv venv
venv\Scripts\activate
```

### macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

## 2. Install packages

```bash
pip install -r requirements.txt
```

## 3. Run the application

```bash
streamlit run app.py
```

Then open the local URL shown in the terminal, normally:

```text
http://localhost:8501
```

## 4. Optional: Enable real AI question generation

The project works without an API key using a local question bank.

For real AI-generated questions, set an OpenAI API key.

### Windows PowerShell

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
```

Optional model:

```powershell
$env:OPENAI_MODEL="gpt-5-mini"
```

Then run:

```bash
streamlit run app.py
```

Never hard-code your API key inside `app.py`.

## Project structure

```text
ai_interview_portal/
│
├── app.py
├── ai_engine.py
├── db.py
├── requirements.txt
├── README.md
├── .gitignore
└── interview_portal.db   # created automatically
```

## How the portal works

1. Candidate registers.
2. Candidate logs in.
3. Candidate uploads a resume.
4. Candidate chooses role, interview type and difficulty.
5. AI generates questions.
6. Candidate answers each question.
7. The evaluator calculates a score and gives feedback.
8. Candidate can save the interview.
9. Dashboard shows average and best performance.

## Recommended future upgrades

- Voice interview using speech-to-text
- Webcam-based interview
- AI facial-expression analysis
- Real-time timer
- Coding editor and code execution
- Admin dashboard
- Question database
- Email reports
- PDF certificate/report generation
- PostgreSQL/MySQL for production
- JWT authentication
- Deployment to Streamlit Community Cloud / Render / AWS
