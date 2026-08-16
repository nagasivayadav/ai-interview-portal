# AI Interview Portal — v2

## Setup

1. Copy these into your project folder (`D:\project-2`), overwriting the old files:
   - `app.py`, `db.py`, `ai_engine.py`, `requirements.txt`
   - The **`.streamlit` folder** (create it if it doesn't exist) with `config.toml`
     inside — this is what applies the new color theme. Folder structure:
     ```
     D:\project-2\.streamlit\config.toml
     D:\project-2\app.py
     ...
     ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run:
   ```
   python -m streamlit run app.py
   ```

## What changed in this version

**Typing test → "Typing Speed Racing" style**
- Pick from 1:00 / 3:00 / 5:00 timed tests or 1/2-page tests, like the screenshots you shared
- Live character-by-character coloring as you type: green = correct, red = wrong, gray = not yet reached
- A countdown timer
- "Test Already Attempted" lock screen after one submission per session (shows your WPM/accuracy), with a button to explicitly start a new test if you want another attempt

**Communication Practice**
- Now starts with a clear "Start Camera & Begin" button instead of dropping you straight into the form
- Camera snapshot + speaking timer + typed transcript → pace and presence scores
- The honest limitation note is still there (see below) — this is not live continuous gesture tracking

**New interview mode: Upload Your Own Q&A Paper**
- On the "New Interview" page there are now two tabs: AI-Generated Questions (as before) and **Upload Your Own Q&A Paper**
- Upload a PDF/DOCX containing your own questions (and optionally answers) in formats like:
  ```
  Q1. What is a REST API?
  A1. An architectural style for web services...

  Q2. ...
  ```
  or `Q: / A:` or a plain numbered list.
- The app asks you those exact questions. If an expected answer was found in the file, your
  typed answer is scored against it (via AI if you've set `OPENAI_API_KEY`, otherwise a
  keyword-overlap heuristic). If no expected answer was found for a question, it falls back
  to general answer-quality scoring.

**New color theme**
- Dark background with amber/orange accent color, card-style panels, styled metrics and buttons
- Comes from `.streamlit/config.toml` (theme colors) + CSS injected at the top of `app.py`

## Still-honest limitation
The Communication Practice page still does **not** do real-time gesture/eye-contact video AI —
that needs a continuous video stream + CV models (e.g. `mediapipe`), which is a different
architecture from Streamlit's page-reload model. This version makes the flow feel more
"camera-first" (matching what you asked for), but the underlying scoring is still the
snapshot + pace approximation, clearly labeled in the UI.