import io
import os
import re
import json
import random

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import docx
except ImportError:
    docx = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def _openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return None
    try:
        return OpenAI(api_key=api_key)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Resume text extraction (PDF + DOCX)
# ---------------------------------------------------------------------------

def extract_resume_text(file_bytes, file_type="pdf"):
    if file_type == "pdf":
        if PdfReader is None:
            return "Install pypdf to extract PDF resumes."
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return text
        except Exception as exc:
            return f"Could not extract PDF text: {exc}"

    elif file_type == "docx":
        if docx is None:
            return "Install python-docx to extract DOCX resumes."
        try:
            document = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join(para.text for para in document.paragraphs)
            return text
        except Exception as exc:
            return f"Could not extract DOCX text: {exc}"

    else:
        return "Unsupported file type."


# ---------------------------------------------------------------------------
# Interview question generation
# ---------------------------------------------------------------------------

_QA_BANK = {
    "easy": [
        ("What interests you about the {role} role?",
         "I'm drawn to the {role} role because it combines hands-on problem-solving with real impact — "
         "I enjoy building things people actually use, and this role lets me keep growing in an area I care about."),
        ("Describe a project you're proud of.",
         "I'm proud of a project where I identified a clear problem, worked closely with others to scope a "
         "practical solution, and delivered something that made a measurable difference for the people using it."),
        ("What are your main technical strengths?",
         "My strongest areas are breaking down problems methodically, writing code that's easy for others to "
         "maintain, and picking up new tools quickly when a project calls for it."),
        ("How do you keep your skills up to date?",
         "I keep learning through hands-on side projects, reading documentation for new tools as they come up, "
         "and following communities where practitioners share what's actually working for them."),
        ("Walk me through your daily workflow.",
         "I usually start by reviewing priorities for the day, spend focused blocks of time on deep work, "
         "check in with teammates as needed, and wrap up by testing and documenting whatever I built."),
    ],
    "medium": [
        ("Describe a challenging problem you solved as a {role}.",
         "I once faced a problem with unclear requirements and tight constraints. I broke it into smaller "
         "pieces, tested my assumptions early, and iterated until I found an approach that held up reliably."),
        ("How do you handle disagreements with teammates?",
         "I try to understand the other person's reasoning first, share my own view with concrete examples, "
         "and focus the conversation on what best serves the shared goal rather than on being right."),
        ("Explain a time you had to learn something quickly.",
         "When I needed to learn something fast, I focused on the essentials first, built a small test case "
         "to check my understanding, and asked for feedback early instead of trying to learn everything upfront."),
        ("How do you prioritize tasks under a tight deadline?",
         "I separate what actually blocks the deadline from what's nice-to-have, tackle the highest-impact and "
         "highest-risk items first, and flag early if something realistically won't make the cut."),
        ("Describe your approach to debugging a tricky issue.",
         "I start by reproducing the issue reliably, narrow down where it's happening using logs or a debugger, "
         "form a specific hypothesis, and test it systematically rather than guessing at fixes."),
    ],
    "hard": [
        ("Design a scalable system relevant to a {role} position.",
         "I'd clarify the expected load and key constraints first, design around a simple and well-tested core, "
         "then add caching and horizontal scaling where the data actually shows it's needed, keeping the system "
         "observable so problems surface early rather than in production."),
        ("Describe a time a project failed and what you learned.",
         "A project I worked on failed partly because we didn't validate a key assumption early enough. It "
         "taught me to surface risks proactively and build in checkpoints so issues show up before they're costly."),
        ("How would you handle a critical production incident?",
         "I'd stabilize the situation first — mitigating impact before chasing the root cause — communicate "
         "status clearly to stakeholders throughout, then run a blameless postmortem afterward to prevent a repeat."),
        ("Explain a trade-off you made between speed and quality.",
         "I once shipped a simpler version of a feature to hit a deadline, while clearly flagging the technical "
         "debt and scheduling time afterward to improve it, rather than letting the shortcut become permanent."),
        ("How do you mentor a struggling teammate?",
         "I start by understanding where they're actually stuck rather than assuming, give them room to work "
         "through problems with guidance instead of just handing over answers, and check in without micromanaging."),
    ],
}


def _local_questions(role, interview_type, difficulty, count, resume_text=""):
    pool = [q.format(role=role) for q, a in _QA_BANK.get(difficulty.lower(), _QA_BANK["medium"])]
    questions = (pool * ((count // len(pool)) + 1))[:count]
    return questions


def _local_qa_pair(role, difficulty):
    pool = _QA_BANK.get(difficulty.lower(), _QA_BANK["medium"])
    q, a = random.choice(pool)
    return q.format(role=role), a.format(role=role)


def generate_questions(role, interview_type, difficulty, count, resume_text=""):
    client = _openai_client()
    if client is None:
        return _local_questions(role, interview_type, difficulty, count, resume_text)

    prompt = f"""Generate {count} {difficulty} {interview_type} interview questions for a {role} position.
{"Base some questions on this resume context: " + resume_text[:2000] if resume_text else ""}
Return ONLY a JSON array of question strings, nothing else."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r"^```json|```$", "", content.strip()).strip()
        questions = json.loads(content)
        return questions[:count]
    except Exception:
        return _local_questions(role, interview_type, difficulty, count, resume_text)


def generate_question_with_answer(role, difficulty):
    """Generate one technical question along with a model/expected answer,
    for modes where the candidate's response should be scored against a
    reference answer (e.g. Communication Practice's technical mode)."""
    client = _openai_client()

    if client is None:
        q, a = _local_qa_pair(role, difficulty)
        return {"question": q, "answer": a}

    prompt = f"""Write one {difficulty} technical interview question for a {role} position,
along with a strong model answer (2-4 sentences) that a great candidate might give.
Return ONLY JSON: {{"question": "<question>", "answer": "<model answer>"}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r"^```json|```$", "", content.strip()).strip()
        result = json.loads(content)
        return {"question": result.get("question", ""), "answer": result.get("answer", "")}
    except Exception:
        q, a = _local_qa_pair(role, difficulty)
        return {"question": q, "answer": a}


# ---------------------------------------------------------------------------
# Answer evaluation
# ---------------------------------------------------------------------------

def evaluate_answer(question_obj, answer):
    client = _openai_client()
    question_text = question_obj if isinstance(question_obj, str) else question_obj.get("question", "")

    if not answer or not answer.strip():
        return {"score": 0, "feedback": "No answer provided."}

    if client is None:
        length_score = min(len(answer.split()) / 40, 1.0) * 6
        keyword_bonus = 2 if len(set(answer.lower().split())) > 15 else 0
        score = round(min(length_score + keyword_bonus + 2, 10), 1)
        return {
            "score": score,
            "feedback": "Local heuristic scoring (no AI key set): based on answer length and vocabulary variety.",
        }

    prompt = f"""Question: {question_text}
Answer: {answer}

Score this answer from 0-10 on relevance, clarity, and depth. Return ONLY JSON like:
{{"score": <number>, "feedback": "<one paragraph>"}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r"^```json|```$", "", content.strip()).strip()
        result = json.loads(content)
        return {"score": float(result.get("score", 0)), "feedback": result.get("feedback", "")}
    except Exception as exc:
        return {"score": 0, "feedback": f"Evaluation failed: {exc}"}


# ---------------------------------------------------------------------------
# Question-paper PDF/DOCX parsing (user-supplied Q&A interview mode)
# ---------------------------------------------------------------------------

def parse_qa_document(file_bytes, file_type="pdf"):
    """Extract a list of {"question": ..., "answer": ...} pairs from an
    uploaded question paper. Supports common patterns:
      Q1. ...        A1. ...
      Q: ...          A: ...
      1) ...          Answer: ...
    If no answer is found for a question, "answer" is left as "".
    """
    raw_text = extract_resume_text(file_bytes, file_type)
    if not raw_text or raw_text.startswith(("Install ", "Could not", "Unsupported")):
        return [], raw_text

    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

    q_pattern = re.compile(r"^(Q\d*[\.\):]|Question\s*\d*[\.\):]|\d+[\.\)])\s*(.*)", re.IGNORECASE)
    a_pattern = re.compile(r"^(A\d*[\.\):]|Ans(?:wer)?\s*\d*[\.\):])\s*(.*)", re.IGNORECASE)

    pairs = []
    current_q = None
    current_a_lines = []
    mode = None  # "q" or "a"

    def flush():
        if current_q is not None:
            pairs.append({"question": current_q.strip(), "answer": " ".join(current_a_lines).strip()})

    for line in lines:
        qm = q_pattern.match(line)
        am = a_pattern.match(line)
        if qm:
            flush()
            current_q = qm.group(2)
            current_a_lines = []
            mode = "q"
        elif am:
            current_a_lines.append(am.group(2))
            mode = "a"
        else:
            if mode == "q":
                current_q = (current_q + " " + line).strip()
            elif mode == "a":
                current_a_lines.append(line)
            # if mode is None (text before first Q marker), ignore

    flush()

    # Fallback: no Q/A markers found at all -> treat each non-empty line as its own question
    if not pairs and lines:
        pairs = [{"question": l, "answer": ""} for l in lines[:20]]

    return pairs, raw_text


def _word_overlap_score(expected, given):
    if not expected.strip():
        return None
    exp_words = set(re.findall(r"[a-z0-9]+", expected.lower()))
    given_words = set(re.findall(r"[a-z0-9]+", given.lower()))
    if not exp_words:
        return None
    overlap = len(exp_words & given_words)
    return round((overlap / len(exp_words)) * 10, 1)


def evaluate_against_expected(question, expected_answer, given_answer):
    """Score a candidate's answer against a known expected answer
    (from an uploaded question paper), using AI if available, otherwise
    a word-overlap heuristic."""

    if not given_answer or not given_answer.strip():
        return {"score": 0, "feedback": "No answer provided."}

    client = _openai_client()

    if client is None or not expected_answer.strip():
        overlap_score = _word_overlap_score(expected_answer, given_answer)
        if overlap_score is None:
            # no expected answer to compare against -> fall back to generic evaluation
            return evaluate_answer(question, given_answer)
        return {
            "score": overlap_score,
            "feedback": f"Local heuristic: matched key terms from the expected answer "
                        f"({overlap_score}/10 based on term overlap).",
        }

    prompt = f"""Question: {question}
Expected/reference answer: {expected_answer}
Candidate's answer: {given_answer}

Score the candidate's answer from 0-10 based on how well it matches the expected
answer's meaning (not exact wording). Return ONLY JSON:
{{"score": <number>, "feedback": "<short paragraph on what was missed or done well>"}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r"^```json|```$", "", content.strip()).strip()
        result = json.loads(content)
        return {"score": float(result.get("score", 0)), "feedback": result.get("feedback", "")}
    except Exception as exc:
        return {"score": 0, "feedback": f"Evaluation failed: {exc}"}


# ---------------------------------------------------------------------------
# Code analysis (correctness + quality)
# ---------------------------------------------------------------------------
def analyze_code(code_text, language_hint="python", expected_behavior=""):
    """Analyze submitted code for correctness (vs expected behavior, if given)
    and general quality (readability, structure, naming, error handling)."""

    if not code_text or not code_text.strip():
        return {"score": 0, "feedback": "No code submitted.", "correctness": 0, "quality": 0}

    client = _openai_client()

    if client is None:
        # Local heuristic: basic static checks, no execution
        quality = 5
        lines = code_text.strip().splitlines()
        if any(len(l) > 100 for l in lines):
            quality -= 1
        if "def " in code_text or "function " in code_text:
            quality += 1
        if re.search(r"#.+|//.+", code_text):
            quality += 1
        if "try" in code_text or "catch" in code_text:
            quality += 1
        quality = max(0, min(quality, 10))
        return {
            "score": quality,
            "correctness": None,
            "quality": quality,
            "feedback": "Local heuristic scoring (no AI key set): checked for functions, comments, "
                        "and error handling. Correctness could not be verified without execution.",
        }

    prompt = f"""You are a technical interviewer. Review this {language_hint} code submission.

{"Expected behavior: " + expected_behavior if expected_behavior else "No specific expected behavior given \u2014 judge general correctness and quality."}

Code:
```
{code_text[:4000]}
```

Return ONLY JSON like:
{{"correctness": <0-10>, "quality": <0-10>, "score": <0-10 overall>, "feedback": "<short paragraph covering bugs, edge cases, and code quality>"}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r"^```json|```$", "", content.strip()).strip()
        result = json.loads(content)
        return {
            "score": float(result.get("score", 0)),
            "correctness": float(result.get("correctness", 0)),
            "quality": float(result.get("quality", 0)),
            "feedback": result.get("feedback", ""),
        }
    except Exception as exc:
        return {"score": 0, "correctness": 0, "quality": 0, "feedback": f"Analysis failed: {exc}"}


def _guess_language(code_text):
    checks = [
        ("python", [r"def \w+\(", r"import \w+", r"print\(", r"self\."]),
        ("javascript", [r"function \w+\(", r"const \w+", r"console\.log", r"=>"]),
        ("java", [r"public class", r"System\.out", r"public static void main"]),
        ("c++", [r"#include", r"std::", r"cout\s*<<"]),
    ]
    for lang, patterns in checks:
        if any(re.search(p, code_text) for p in patterns):
            return lang
    return "unknown"


def explain_code(code_text, language_hint="auto"):
    """Explain what a piece of code does: detected language, a step-by-step
    walkthrough of its logic, and the expected output/behavior — instead of
    scoring it. Used for learning/interview-prep, not grading."""

    if not code_text or not code_text.strip():
        return {"language": "unknown", "explanation": "No code submitted.", "expected_output": ""}

    detected_lang = _guess_language(code_text) if language_hint in ("auto", "", None) else language_hint
    client = _openai_client()

    if client is None:
        lines = [l for l in code_text.splitlines() if l.strip()]
        func_count = len(re.findall(r"def \w+\(|function \w+\(", code_text))
        loop_count = len(re.findall(r"\bfor\b|\bwhile\b", code_text))
        cond_count = len(re.findall(r"\bif\b", code_text))
        explanation = (
            f"Local heuristic summary (no AI key set): this looks like {detected_lang} code with "
            f"{len(lines)} non-empty lines, {func_count} function definition(s), {loop_count} loop(s), "
            f"and {cond_count} conditional(s). For a full line-by-line walkthrough and predicted output, "
            f"set OPENAI_API_KEY."
        )
        return {"language": detected_lang, "explanation": explanation, "expected_output": "Not available without AI key."}

    prompt = f"""Identify the programming language of this code, then explain step-by-step how it works
(walk through the logic in plain English, in order), and state what the output/result would be
if it were run (or its general behavior if it doesn't produce direct output).

Code:
```
{code_text[:4000]}
```

Return ONLY JSON:
{{"language": "<detected language>", "explanation": "<step-by-step walkthrough as numbered points, plain text>", "expected_output": "<what running this produces, or its behavior>"}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r"^```json|```$", "", content.strip()).strip()
        result = json.loads(content)
        return {
            "language": result.get("language", detected_lang),
            "explanation": result.get("explanation", ""),
            "expected_output": result.get("expected_output", ""),
        }
    except Exception as exc:
        return {"language": detected_lang, "explanation": f"Explanation failed: {exc}", "expected_output": ""}


# ---------------------------------------------------------------------------
# Communication / presence scoring (lightweight, snapshot-based)
# ---------------------------------------------------------------------------

def score_communication(transcript_text, elapsed_seconds, snapshot_captured):
    """Heuristic communication score.

    IMPORTANT LIMITATION: real-time video gesture/eye-contact tracking needs
    heavy CV models (mediapipe/opencv) and a live video pipeline, which
    Streamlit's request-response model doesn't support well. This gives a
    practical approximation instead:
      - Pace: words-per-minute of the typed/transcribed response
      - Presence: whether a camera snapshot was captured at all
    Treat this as a directional signal, not a certified gesture analysis.
    """
    words = len(transcript_text.split()) if transcript_text else 0
    minutes = max(elapsed_seconds / 60, 0.01)
    wpm = words / minutes

    # Ideal spoken pace ~110-160 wpm
    if 110 <= wpm <= 160:
        pace_score = 10
    else:
        pace_score = max(0, 10 - abs(wpm - 135) / 10)

    presence_score = 8 if snapshot_captured else 3
    overall = round((pace_score * 0.6 + presence_score * 0.4), 1)

    feedback_parts = [f"Estimated pace: {wpm:.0f} words/min."]
    if wpm < 110:
        feedback_parts.append("Consider speaking a bit faster/more concisely.")
    elif wpm > 160:
        feedback_parts.append("Consider slowing down slightly for clarity.")
    else:
        feedback_parts.append("Pace is in a good conversational range.")
    feedback_parts.append(
        "Camera snapshot captured." if snapshot_captured else "No camera snapshot captured — presence could not be checked."
    )

    return {
        "pace_score": round(pace_score, 1),
        "presence_score": presence_score,
        "overall_score": overall,
        "feedback": " ".join(feedback_parts),
    }


def score_talk_about_info(source_text, transcript_text, elapsed_seconds, snapshot_captured):
    """For the 'talk about my uploaded info' mode: scores both delivery
    (pace/presence, same as score_communication) and content accuracy —
    how well the transcript actually reflects the uploaded source document."""

    base = score_communication(transcript_text, elapsed_seconds, snapshot_captured)

    client = _openai_client()
    if client is None or not source_text.strip():
        content_score = _word_overlap_score(source_text, transcript_text) or 0
        content_feedback = f"Local heuristic: transcript covers {content_score}/10 of key terms from your uploaded info."
    else:
        prompt = f"""Source information (what the person should talk about):
{source_text[:2500]}

What they actually said (transcript):
{transcript_text}

Score 0-10 how accurately and completely the transcript reflects the source information.
Return ONLY JSON: {{"score": <number>, "feedback": "<short paragraph, what was covered/missed>"}}"""
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
            )
            content = response.choices[0].message.content.strip()
            content = re.sub(r"^```json|```$", "", content.strip()).strip()
            result = json.loads(content)
            content_score = float(result.get("score", 0))
            content_feedback = result.get("feedback", "")
        except Exception as exc:
            content_score = 0
            content_feedback = f"Content scoring failed: {exc}"

    overall = round((base["overall_score"] * 0.5 + content_score * 0.5), 1)
    return {
        "pace_score": base["pace_score"],
        "presence_score": base["presence_score"],
        "content_score": round(content_score, 1),
        "overall_score": overall,
        "feedback": base["feedback"] + " | Content: " + content_feedback,
    }


# ---------------------------------------------------------------------------
# Typing test scoring
# ---------------------------------------------------------------------------

def generate_typing_passage(avoid_text=""):
    """Return a typing-test passage. Uses AI to generate a fresh one when a
    key is set (so text varies every attempt); otherwise picks a different
    entry from the local pool than the one just used."""
    client = _openai_client()
    if client is not None:
        prompt = ("Write one natural, flowing English paragraph of about 35-45 words, "
                   "suitable for a typing speed test. Plain prose, no lists, no quotes marks. "
                   "Return ONLY the paragraph text, nothing else.")
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
            )
            text = response.choices[0].message.content.strip()
            if text and text != avoid_text:
                return text
        except Exception:
            pass

    pool = [p for p in TYPING_PASSAGE_POOL if p != avoid_text] or TYPING_PASSAGE_POOL
    import random as _r
    return _r.choice(pool)


TYPING_PASSAGE_POOL = [
    "The quick brown fox jumps over the lazy dog while the sun sets slowly behind the hills, "
    "casting long shadows across the quiet meadow where children once played every summer evening.",
    "Effective communication in a professional setting requires clarity, patience, and the ability "
    "to listen actively before responding with well-considered feedback that moves the conversation forward.",
    "Technology continues to reshape the way people work, learn, and connect with one another, "
    "creating both new opportunities and new challenges that require thoughtful, adaptable solutions.",
    "Success rarely arrives overnight; it is usually the quiet result of small, consistent efforts "
    "repeated patiently over weeks and months until progress finally becomes visible to others.",
    "A well-organized morning routine can set the tone for an entire day, giving structure to tasks "
    "that might otherwise feel overwhelming once emails, meetings, and deadlines start piling up.",
    "Good design is rarely about adding more; it is about removing everything unnecessary until only "
    "the essential pieces remain, each one earning its place through clarity and genuine usefulness.",
]


def score_typing_test(reference_text, typed_text, elapsed_seconds):
    ref_words = reference_text.strip().split()
    typed_words = typed_text.strip().split()

    minutes = max(elapsed_seconds / 60, 0.01)
    wpm = len(typed_words) / minutes

    correct = sum(1 for a, b in zip(ref_words, typed_words) if a == b)
    total = max(len(ref_words), 1)
    accuracy = round((correct / total) * 100, 1)

    return {"wpm": round(wpm, 1), "accuracy": accuracy}


def diff_chars_html(reference_text, typed_text):
    """Build character-by-character colored HTML: green = correct,
    red = incorrect, dim = not yet typed. Used for the live typing-race view."""
    spans = []
    for i, ch in enumerate(reference_text):
        display_ch = ch if ch != " " else "&nbsp;"
        if i < len(typed_text):
            if typed_text[i] == ch:
                spans.append(f'<span style="color:#34d399">{display_ch}</span>')
            else:
                spans.append(f'<span style="color:#f87171;text-decoration:underline">{display_ch}</span>')
        else:
            spans.append(f'<span style="color:#64748b">{display_ch}</span>')
    return "".join(spans)


def diff_typing_html(reference_text, typed_text):
    """Typing.com-style rendering: full paragraph wraps across multiple lines.
    Completed words get a green (correct) or red (wrong) background. The
    word currently being typed shows per-character coloring plus a blue
    cursor bar right at the next character to type. Untyped words stay plain.
    """
    words = reference_text.split(" ")
    typed_len = len(typed_text)

    parts = []
    pos = 0
    for word in words:
        start, end = pos, pos + len(word)

        if typed_len > end:
            # word is fully behind the cursor -> whole-word correct/incorrect
            typed_word = typed_text[start:end]
            if typed_word == word:
                style = "background:#134e2a;color:#4ade80;"
            else:
                style = "background:#4c1d24;color:#f87171;text-decoration:line-through;"
            parts.append(f'<span style="{style}border-radius:4px;padding:1px 3px;">{word}</span>')

        elif start <= typed_len <= end:
            # word currently being typed -> per-character + cursor
            chars = []
            for ci, ch in enumerate(word):
                abs_i = start + ci
                if abs_i < typed_len:
                    ok = typed_text[abs_i] == ch
                    color = "#4ade80" if ok else "#f87171"
                    chars.append(f'<span style="color:{color}">{ch}</span>')
                elif abs_i == typed_len:
                    chars.append(f'<span id="typing-cursor" style="border-left:2px solid #818cf8;">{ch}</span>')
                else:
                    chars.append(f'<span>{ch}</span>')
            parts.append("".join(chars))

        else:
            parts.append(f'<span>{word}</span>')

        pos = end + 1  # account for the space between words

    return " ".join(parts)