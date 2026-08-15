import streamlit as st
from datetime import datetime
from pathlib import Path
from db import (
    init_db, create_user, authenticate_user, save_interview,
    get_user_interviews, get_user_stats
)
from ai_engine import generate_questions, evaluate_answer, extract_resume_text

st.set_page_config(
    page_title="AI Interview Portal",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

# ---------- Styling ----------
st.markdown("""
<style>
.main {background: #f7f9fc;}
.hero {
    padding: 30px;
    border-radius: 18px;
    background: linear-gradient(135deg,#111827,#2563eb);
    color: white;
    margin-bottom: 22px;
}
.card {
    padding: 20px;
    border-radius: 16px;
    background: white;
    border: 1px solid #e5e7eb;
    margin-bottom: 14px;
}
.question {
    padding: 18px;
    border-radius: 14px;
    background: #eef4ff;
    border-left: 5px solid #2563eb;
    font-size: 18px;
}
.small {color:#6b7280;}
</style>
""", unsafe_allow_html=True)

# ---------- Session ----------
defaults = {
    "user": None,
    "page": "Login",
    "questions": [],
    "answers": [],
    "current_q": 0,
    "interview_meta": {},
    "results": [],
    "resume_text": "",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

def go(page):
    st.session_state.page = page
    st.rerun()

# ---------- Auth ----------
def auth_page():
    st.markdown("""
    <div class="hero">
        <h1>🤖 AI Interview Portal</h1>
        <p>Practice technical, HR and behavioral interviews with an AI-powered evaluator.</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
            if submitted:
                user = authenticate_user(email, password)
                if user:
                    st.session_state.user = user
                    st.session_state.page = "Dashboard"
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

    with tab2:
        with st.form("register_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Password", type="password", key="reg_password")
            confirm = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Create Account", use_container_width=True)

            if submitted:
                if not name or not email or not password:
                    st.warning("Please fill all fields.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                elif len(password) < 6:
                    st.error("Password must contain at least 6 characters.")
                else:
                    ok, message = create_user(name, email, password)
                    if ok:
                        st.success(message + " You can now login.")
                    else:
                        st.error(message)

# ---------- Dashboard ----------
def dashboard():
    user = st.session_state.user
    stats = get_user_stats(user["id"])

    st.markdown(f"""
    <div class="hero">
        <h1>Welcome, {user["name"]} 👋</h1>
        <p>Track your interview preparation and improve your performance.</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Interviews", stats["count"])
    c2.metric("Average Score", f'{stats["avg"]:.1f}/100')
    c3.metric("Best Score", f'{stats["best"]:.1f}/100')
    c4.metric("Latest Role", stats["latest_role"] or "-")

    st.markdown("### 🚀 Start practicing")
    a, b, c = st.columns(3)
    if a.button("🎯 New Interview", use_container_width=True):
        go("New Interview")
    if b.button("📊 My Results", use_container_width=True):
        go("Results")
    if c.button("📄 Resume Analyzer", use_container_width=True):
        go("Resume")

# ---------- New Interview ----------
def new_interview():
    st.title("🎯 Create AI Interview")

    with st.form("interview_setup"):
        role = st.selectbox(
            "Target Role",
            ["Python Developer", "Data Analyst", "Software Developer",
             "Web Developer", "Data Scientist", "HR / General"]
        )
        interview_type = st.selectbox(
            "Interview Type", ["Technical", "HR", "Behavioral", "Mixed"]
        )
        difficulty = st.select_slider(
            "Difficulty", options=["Easy", "Medium", "Hard"], value="Medium"
        )
        count = st.slider("Number of Questions", 3, 10, 5)
        generate = st.form_submit_button("🤖 Generate Interview", use_container_width=True)

    if generate:
        with st.spinner("AI is preparing your interview..."):
            qs = generate_questions(
                role, interview_type, difficulty, count,
                st.session_state.resume_text
            )
        st.session_state.questions = qs
        st.session_state.answers = []
        st.session_state.results = []
        st.session_state.current_q = 0
        st.session_state.interview_meta = {
            "role": role,
            "type": interview_type,
            "difficulty": difficulty,
        }
        go("Interview")

# ---------- Interview ----------
def interview_page():
    questions = st.session_state.questions
    idx = st.session_state.current_q

    if not questions:
        st.warning("No interview is active.")
        if st.button("Create Interview"):
            go("New Interview")
        return

    total = len(questions)
    st.progress(idx / total if idx < total else 1.0)
    st.caption(f"Question {min(idx+1,total)} of {total}")

    if idx >= total:
        finish_interview()
        return

    q = questions[idx]
    st.markdown(f'<div class="question"><b>Q{idx+1}.</b> {q["question"]}</div>',
                unsafe_allow_html=True)
    st.write("")

    answer = st.text_area(
        "Your Answer",
        height=180,
        placeholder="Type your answer as if you were speaking to the interviewer...",
        key=f"answer_{idx}"
    )

    col1, col2 = st.columns([1, 1])
    if col1.button("Submit Answer ➜", use_container_width=True):
        if not answer.strip():
            st.warning("Please enter an answer.")
        else:
            evaluation = evaluate_answer(q, answer)
            st.session_state.answers.append({
                "question": q["question"],
                "answer": answer,
                "evaluation": evaluation
            })
            st.session_state.current_q += 1
            st.rerun()

    if col2.button("Exit Interview", use_container_width=True):
        st.session_state.questions = []
        go("Dashboard")

def finish_interview():
    results = st.session_state.answers
    if not results:
        go("Dashboard")
        return

    if not st.session_state.results:
        st.session_state.results = results

    scores = [r["evaluation"]["score"] for r in results]
    overall = sum(scores) / len(scores)

    st.balloons()
    st.markdown(f"""
    <div class="hero">
        <h1>🎉 Interview Completed</h1>
        <h2>Overall Score: {overall:.1f}/100</h2>
        <p>Role: {st.session_state.interview_meta.get("role","-")}</p>
    </div>
    """, unsafe_allow_html=True)

    for i, item in enumerate(results, 1):
        ev = item["evaluation"]
        with st.expander(f"Q{i}: {item['question']} — {ev['score']}/100"):
            st.write("**Your answer:**", item["answer"])
            st.write("**Feedback:**", ev["feedback"])
            st.write("**Strengths:**", ", ".join(ev["strengths"]) or "Needs improvement")
            st.write("**Suggestions:**", ", ".join(ev["suggestions"]) or "Keep practicing")

    if st.button("💾 Save Interview Result", use_container_width=True):
        save_interview(
            st.session_state.user["id"],
            st.session_state.interview_meta,
            overall,
            results
        )
        st.success("Interview result saved successfully.")
        st.session_state.questions = []
        st.session_state.answers = []
        st.session_state.current_q = 0

    if st.button("🏠 Back to Dashboard", use_container_width=True):
        go("Dashboard")

# ---------- Results ----------
def results_page():
    st.title("📊 Interview History")
    rows = get_user_interviews(st.session_state.user["id"])

    if not rows:
        st.info("No saved interviews yet.")
        return

    for row in rows:
        with st.expander(
            f'{row["role"]} • {row["interview_type"]} • {row["score"]:.1f}/100 • {row["created_at"]}'
        ):
            st.write("**Difficulty:**", row["difficulty"])
            st.write("**Questions:**", row["question_count"])
            st.write("**Score:**", f'{row["score"]:.1f}/100')

# ---------- Resume ----------
def resume_page():
    st.title("📄 Resume Analyzer")
    st.write("Upload a PDF resume. The portal extracts text and uses it as interview context.")

    uploaded = st.file_uploader("Upload Resume", type=["pdf", "txt"])

    if uploaded:
        if uploaded.name.lower().endswith(".pdf"):
            text = extract_resume_text(uploaded.read())
        else:
            text = uploaded.read().decode("utf-8", errors="ignore")

        st.session_state.resume_text = text[:12000]

        st.success("Resume loaded successfully.")
        st.write("### Extracted Resume Text")
        st.text_area("Resume", st.session_state.resume_text, height=300)

        st.info("Start a new interview to generate questions based on your resume.")

# ---------- Sidebar ----------
def sidebar():
    if st.session_state.user:
        st.sidebar.success(f'Logged in as {st.session_state.user["name"]}')
        pages = ["Dashboard", "New Interview", "Resume", "Results"]
        selected = st.sidebar.radio("Navigation", pages, index=pages.index(st.session_state.page)
                                    if st.session_state.page in pages else 0)
        if selected != st.session_state.page:
            st.session_state.page = selected
            st.rerun()

        if st.sidebar.button("🚪 Logout", use_container_width=True):
            st.session_state.user = None
            st.session_state.page = "Login"
            st.session_state.questions = []
            st.rerun()

        st.sidebar.markdown("---")
        st.sidebar.caption("AI Interview Portal • Python + Streamlit + SQLite")

# ---------- Router ----------
if st.session_state.user:
    sidebar()
    page = st.session_state.page
    if page == "Dashboard":
        dashboard()
    elif page == "New Interview":
        new_interview()
    elif page == "Interview":
        interview_page()
    elif page == "Resume":
        resume_page()
    elif page == "Results":
        results_page()
else:
    auth_page()
