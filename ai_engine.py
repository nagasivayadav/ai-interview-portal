import os
import re
import random
from collections import Counter

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

# Optional real AI integration.
# If OPENAI_API_KEY is present and openai is installed, the portal can use
# the OpenAI Responses API. Otherwise it falls back to the local question bank.

def _openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except Exception:
        return None

def _local_questions(role, interview_type, difficulty, count, resume_text=""):
    role_key = role.lower()

    bank = {
        "python developer": [
            ("Explain the difference between a list, tuple and set in Python.", ["list","tuple","set"]),
            ("What are decorators in Python and where would you use them?", ["decorator","function","wrapper"]),
            ("Explain exception handling using try, except, else and finally.", ["try","except","finally"]),
            ("What is the difference between shallow copy and deep copy?", ["shallow","deep","copy"]),
            ("How does a Python dictionary work at a high level?", ["hash","key","value"]),
            ("Explain object-oriented programming concepts in Python.", ["class","object","inheritance","polymorphism"]),
        ],
        "data analyst": [
            ("What is the difference between mean, median and mode?", ["mean","median","mode"]),
            ("How would you handle missing values in a dataset?", ["missing","null","impute","drop"]),
            ("Explain the difference between INNER JOIN and LEFT JOIN.", ["inner","left","join"]),
            ("What is the purpose of data visualization?", ["visual","insight","pattern","chart"]),
            ("Explain a dashboard you have built and the business insight it provided.", ["dashboard","insight","business"]),
            ("How would you validate the quality of a dataset?", ["quality","duplicate","missing","validation"]),
        ],
        "software developer": [
            ("Explain the software development life cycle.", ["requirements","development","testing","deployment"]),
            ("What is the difference between REST and SOAP?", ["rest","soap","api"]),
            ("Explain Git branching and why teams use branches.", ["git","branch","merge"]),
            ("What is a database index and why is it useful?", ["index","query","database"]),
            ("Explain the difference between authentication and authorization.", ["authentication","authorization"]),
            ("How do you debug a difficult production issue?", ["logs","debug","reproduce","monitor"]),
        ],
        "web developer": [
            ("What is the difference between HTML, CSS and JavaScript?", ["html","css","javascript"]),
            ("Explain responsive web design.", ["responsive","screen","mobile"]),
            ("What is an API and how does a frontend communicate with it?", ["api","request","response"]),
            ("Explain client-side versus server-side rendering.", ["client","server","render"]),
            ("What is the purpose of HTTP status codes?", ["http","status","200","404"]),
        ],
        "data scientist": [
            ("Explain the difference between supervised and unsupervised learning.", ["supervised","unsupervised","label"]),
            ("What is overfitting and how can you reduce it?", ["overfitting","regularization","validation"]),
            ("Explain precision, recall and F1-score.", ["precision","recall","f1"]),
            ("What is feature engineering?", ["feature","transform","variable"]),
            ("Explain the purpose of train, validation and test sets.", ["train","validation","test"]),
        ],
        "hr / general": [
            ("Tell me about yourself and your technical background.", ["background","skill","experience"]),
            ("Why do you want this role?", ["role","interest","skill"]),
            ("Describe a difficult project and how you solved the problem.", ["problem","solution","project"]),
            ("What is one weakness you are actively improving?", ["weakness","improve","learning"]),
            ("Where do you see yourself in the next three years?", ["goal","career","growth"]),
        ],
    }

    selected = bank.get(role_key, bank["software developer"])

    if interview_type.lower() == "hr":
        selected = bank["hr / general"]
    elif interview_type.lower() == "behavioral":
        selected = [
            ("Describe a time you disagreed with a teammate. What did you do?", ["team","disagree","communication"]),
            ("Tell me about a failure and what you learned from it.", ["failure","learn","improve"]),
            ("Describe a time you worked under a tight deadline.", ["deadline","priority","result"]),
            ("Tell me about a situation where you took initiative.", ["initiative","action","result"]),
        ]

    if resume_text:
        # Add one resume-context question.
        terms = re.findall(r"\b[A-Za-z][A-Za-z0-9+#.-]{2,}\b", resume_text)
        common = [w for w, n in Counter(t.lower() for t in terms).most_common(30)
                  if w not in {"the","and","with","from","this","that","your","you"}]
        if common:
            selected = selected + [
                (f"Your resume mentions {common[0]}. Explain your hands-on experience with it.",
                 [common[0], "project", "experience"])
            ]

    random.shuffle(selected)
    selected = selected[:count]

    return [
        {
            "question": q,
            "keywords": keywords,
            "difficulty": difficulty,
            "type": interview_type,
        }
        for q, keywords in selected
    ]

def generate_questions(role, interview_type, difficulty, count, resume_text=""):
    client = _openai_client()

    if client:
        try:
            prompt = f"""
Create exactly {count} interview questions for a candidate applying for:
Role: {role}
Interview type: {interview_type}
Difficulty: {difficulty}

Resume context:
{resume_text[:6000]}

Return ONLY a JSON array. Each item must have:
question: string
keywords: array of 3-6 short strings

Questions should be practical, non-repetitive, and suitable for a college/job interview.
"""
            response = client.responses.create(
                model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
                input=prompt,
                store=False,
            )
            import json
            data = json.loads(response.output_text)
            if isinstance(data, list) and data:
                return data[:count]
        except Exception:
            pass

    return _local_questions(role, interview_type, difficulty, count, resume_text)

def evaluate_answer(question_obj, answer):
    answer_clean = answer.strip()
    words = re.findall(r"[A-Za-z0-9+#.-]+", answer_clean.lower())
    word_count = len(words)

    keywords = [str(k).lower() for k in question_obj.get("keywords", [])]
    matched = [k for k in keywords if any(k in w or w in k for w in words)]

    keyword_score = (len(matched) / max(len(keywords), 1)) * 60
    length_score = min(25, word_count / 4) if word_count < 100 else 25

    structure_terms = ["because", "therefore", "example", "first", "then", "finally"]
    structure_score = min(15, sum(t in answer_clean.lower() for t in structure_terms) * 3)

    score = round(min(100, keyword_score + length_score + structure_score), 1)

    strengths = []
    suggestions = []

    if len(matched) >= max(1, len(keywords)//2):
        strengths.append("Covered important concepts")
    else:
        suggestions.append("Include more role-specific technical concepts")

    if word_count >= 50:
        strengths.append("Provided a reasonably detailed answer")
    else:
        suggestions.append("Give a more detailed answer with an example")

    if structure_score >= 6:
        strengths.append("Answer has a clear structure")
    else:
        suggestions.append("Use a simple structure: situation, action, result")

    if score >= 80:
        feedback = "Strong answer. Keep it concise and support technical points with examples."
    elif score >= 60:
        feedback = "Good attempt. Add more specific concepts, examples and measurable results."
    else:
        feedback = "The answer needs more depth. Explain the concept clearly and connect it to a real example."

    return {
        "score": score,
        "feedback": feedback,
        "strengths": strengths,
        "suggestions": suggestions,
        "matched_keywords": matched,
    }

def extract_resume_text(file_bytes):
    if PdfReader is None:
        return "Install pypdf to extract PDF resumes."

    try:
        import io
        reader = PdfReader(io.BytesIO(file_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text
    except Exception as exc:
        return f"Could not extract PDF text: {exc}"
