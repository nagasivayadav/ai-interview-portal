import time
import random
import streamlit as st

from db import (
    init_db, create_user, get_user, create_interview, save_result,
    save_typing_result, save_communication_result,
    get_user_results, get_user_typing_results, get_user_communication_results,
    get_all_candidates_summary,
)
from ai_engine import (
    generate_questions, evaluate_answer, extract_resume_text,
    analyze_code, score_communication, score_typing_test,
    parse_qa_document, evaluate_against_expected, diff_chars_html, diff_typing_html,
    explain_code, score_talk_about_info, generate_typing_passage, generate_question_with_answer,
)

st.set_page_config(page_title="AI Interview Portal", page_icon="🎯", layout="wide")

init_db()

# ---------------------------------------------------------------------------
# Global styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .stApp { background: linear-gradient(180deg, #0a0e1f 0%, #12173080 100%); }

    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #151a35, #1c234d80);
        border: 1px solid #2e3564;
        border-radius: 14px;
        padding: 16px 18px;
    }
    div[data-testid="stMetric"] label { color: #94a3f0 !important; }

    .stButton > button {
        border-radius: 10px;
        border: 1px solid #818cf840;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: #f8fafc;
        font-weight: 600;
        transition: transform 0.08s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        border-color: #818cf8;
        color: #ffffff;
    }

    .portal-card {
        background: linear-gradient(135deg, #151a3599, #1c234d99);
        border: 1px solid #2e3564;
        border-radius: 16px;
        padding: 22px 26px;
        margin-bottom: 14px;
    }

    .teleprompter-card {
        background: linear-gradient(160deg, #12173a, #0a0e1f);
        border: 1px solid #6366f150;
        border-radius: 16px;
        padding: 26px 28px;
        min-height: 320px;
        font-size: 1.15rem;
        line-height: 1.9rem;
    }
    .teleprompter-card .tp-label {
        color: #818cf8;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .teleprompter-card .tp-question {
        color: #f1f5f9;
        font-weight: 600;
        margin-bottom: 20px;
    }
    .teleprompter-card .tp-answer {
        color: #a5b4fc;
        font-family: 'Courier New', monospace;
    }

    .typing-paragraph {
        background: #080b18;
        border: 1px solid #2e3564;
        border-radius: 14px 14px 0 0;
        border-bottom: none;
        padding: 22px 24px;
        font-family: 'Courier New', monospace;
        font-size: 1.2rem;
        line-height: 2.4rem;
        letter-spacing: 0.3px;
        white-space: normal;
        word-wrap: break-word;
        max-height: 220px;
        overflow-y: hidden;
        scroll-behavior: smooth;
    }

    input[aria-label="Type here"] {
        background: #0b0e1c !important;
        border: 1px solid #2e3564 !important;
        border-top: none !important;
        border-radius: 0 0 14px 14px !important;
        font-family: 'Courier New', monospace !important;
        font-size: 1rem !important;
        letter-spacing: 0.3px !important;
        color: #64748b !important;
        caret-color: #818cf8 !important;
        padding: 10px 16px !important;
    }

    h1, h2, h3 { color: #f1f5f9 !important; }

    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #12173a, #0a0e1f);
        border-right: 1px solid #2e3564;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session defaults
# ---------------------------------------------------------------------------
defaults = {
    "page": "auth",
    "user": None,
    "resume_text": "",
    "questions": [],
    "current_q": 0,
    "interview_id": None,
    "answers": [],
    "typing_start": None,
    "typing_locked": False,
    "typing_duration_label": "1:00 Test",
    "comm_start": None,
    "comm_snapshot": None,
    "comm_camera_on": False,
    "qa_pairs": [],
    "qa_source_name": "",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def go(page):
    st.session_state.page = page
    st.rerun()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def auth_page():
    st.title("🎯 AI Interview Portal")
    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        u = st.text_input("Username", key="login_u")
        p = st.text_input("Password", type="password", key="login_p")
        if st.button("Login", use_container_width=True):
            user = get_user(u, p)
            if user:
                st.session_state.user = user
                go("dashboard")
            else:
                st.error("Invalid username or password.")

    with tab_register:
        u = st.text_input("Choose a username", key="reg_u")
        p = st.text_input("Choose a password", type="password", key="reg_p")
        if st.button("Register", use_container_width=True):
            if not u or not p:
                st.error("Username and password are required.")
            else:
                try:
                    create_user(u, p)
                    st.success("Account created. Please log in.")
                except Exception:
                    st.error("That username is already taken.")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
def dashboard():
    st.title("📊 Dashboard")
    user = st.session_state.user
    results = get_user_results(user["id"])
    typing_results = get_user_typing_results(user["id"])
    comm_results = get_user_communication_results(user["id"])

    col1, col2, col3, col4 = st.columns(4)
    avg_score = round(sum(r["score"] for r in results) / len(results), 1) if results else 0
    col1.metric("Interview Answers", len(results))
    col2.metric("Average Score", f"{avg_score}/10")
    col3.metric("Typing Tests Taken", len(typing_results))
    col4.metric("Comm. Sessions", len(comm_results))

    st.divider()

    st.subheader("Past Interview Results")
    if results:
        st.dataframe(
            [{"Date": r["created_at"], "Role": r["role"], "Question": r["question"][:60],
              "Score": r["score"], "Category": r["category"]} for r in results],
            use_container_width=True,
        )
        try:
            import pandas as pd
            df = pd.DataFrame(results)
            df["created_at"] = pd.to_datetime(df["created_at"])
            df = df.sort_values("created_at")
            st.line_chart(df.set_index("created_at")["score"])
        except Exception:
            pass
    else:
        st.info("No interview results yet — take an interview to see your progress here.")

    st.subheader("Typing Test History")
    if typing_results:
        st.dataframe(
            [{"Date": t["created_at"], "WPM": t["wpm"], "Accuracy %": t["accuracy"]} for t in typing_results],
            use_container_width=True,
        )
    else:
        st.info("No typing tests yet.")

    st.subheader("Communication Practice History")
    if comm_results:
        st.dataframe(
            [{"Date": c["created_at"], "Pace Score": c["pace_score"],
              "Presence Score": c["presence_score"], "Overall": c["overall_score"]} for c in comm_results],
            use_container_width=True,
        )
    else:
        st.info("No communication practice sessions yet.")

    if user["username"] == "admin":
        st.divider()
        st.subheader("🛠 Admin: All Candidates")
        summary = get_all_candidates_summary()
        st.dataframe(summary, use_container_width=True)


# ---------------------------------------------------------------------------
# New interview setup
# ---------------------------------------------------------------------------
def new_interview():
    st.title("🆕 New Interview")

    tab_ai, tab_upload = st.tabs(["🤖 AI-Generated Questions", "📎 Upload Your Own Q&A Paper"])

    with tab_ai:
        role = st.text_input("Target Role", value="Software Engineer")
        interview_type = st.selectbox("Interview Type", ["Behavioral", "Technical", "Mixed"])
        difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
        count = st.slider("Number of Questions", 3, 10, 5)

        use_resume = st.checkbox("Use uploaded resume as context", value=bool(st.session_state.resume_text))

        if st.button("Generate Questions", use_container_width=True):
            resume_context = st.session_state.resume_text if use_resume else ""
            with st.spinner("Generating questions..."):
                questions = generate_questions(role, interview_type, difficulty, count, resume_context)
            interview_id = create_interview(st.session_state.user["id"], role, interview_type, difficulty)
            st.session_state.questions = questions
            st.session_state.qa_pairs = []  # AI mode has no expected-answer pairs
            st.session_state.interview_id = interview_id
            st.session_state.current_q = 0
            st.session_state.answers = []
            go("interview")

    with tab_upload:
        st.write("Upload a PDF or DOCX with your own questions (and optionally answers). "
                 "The portal will ask you these questions and, where an expected answer was "
                 "found in the file, score your response against it.")
        st.caption("Supported formats inside the file: `Q1. ... A1. ...`, `Q: ... A: ...`, "
                    "or a numbered list `1) ...` (answers optional).")

        qa_file = st.file_uploader("Upload Question Paper", type=["pdf", "docx"], key="qa_file")

        if qa_file and st.button("Parse & Start Interview", use_container_width=True):
            file_type = qa_file.name.lower().split(".")[-1]
            with st.spinner("Reading your question paper..."):
                pairs, raw_text = parse_qa_document(qa_file.read(), file_type)

            if not pairs:
                st.error("Couldn't find any questions in that file. Try a clearer format "
                         "(e.g. 'Q1. ...' on its own line).")
            else:
                interview_id = create_interview(
                    st.session_state.user["id"], "Custom Q&A Paper", "Uploaded", "N/A"
                )
                st.session_state.questions = [p["question"] for p in pairs]
                st.session_state.qa_pairs = pairs
                st.session_state.interview_id = interview_id
                st.session_state.current_q = 0
                st.session_state.answers = []
                st.session_state.qa_source_name = qa_file.name
                go("interview")


# ---------------------------------------------------------------------------
# Interview flow
# ---------------------------------------------------------------------------
def interview_page():
    st.title("🎤 Interview")
    questions = st.session_state.questions
    idx = st.session_state.current_q

    if not questions:
        st.warning("No questions loaded. Start a new interview first.")
        if st.button("Go to New Interview"):
            go("new_interview")
        return

    if idx >= len(questions):
        go("finish_interview")
        return

    st.progress((idx) / len(questions))
    if st.session_state.qa_pairs:
        st.caption(f"From your uploaded paper: {st.session_state.qa_source_name}")
    st.subheader(f"Question {idx + 1} of {len(questions)}")
    st.write(questions[idx])

    answer = st.text_area("Your answer", key=f"answer_{idx}", height=150)

    if st.button("Submit Answer", use_container_width=True):
        with st.spinner("Evaluating..."):
            if st.session_state.qa_pairs and idx < len(st.session_state.qa_pairs):
                expected = st.session_state.qa_pairs[idx].get("answer", "")
                result = evaluate_against_expected(questions[idx], expected, answer)
            else:
                result = evaluate_answer(questions[idx], answer)
        save_result(st.session_state.interview_id, questions[idx], answer, result["score"], result["feedback"])
        st.session_state.answers.append({"question": questions[idx], "answer": answer, **result})
        st.session_state.current_q += 1
        st.rerun()


def finish_interview():
    st.title("✅ Interview Complete")
    answers = st.session_state.answers
    if answers:
        avg = round(sum(a["score"] for a in answers) / len(answers), 1)
        st.metric("Average Score", f"{avg}/10")
        for i, a in enumerate(answers, 1):
            with st.expander(f"Q{i}: {a['question'][:70]}"):
                st.write(f"**Your answer:** {a['answer']}")
                st.write(f"**Score:** {a['score']}/10")
                st.write(f"**Feedback:** {a['feedback']}")
    else:
        st.info("No answers recorded.")

    if st.button("Back to Dashboard", use_container_width=True):
        st.session_state.questions = []
        st.session_state.answers = []
        st.session_state.current_q = 0
        go("dashboard")


# ---------------------------------------------------------------------------
# Resume upload
# ---------------------------------------------------------------------------
def resume_page():
    st.title("📄 Resume Analyzer")
    st.write("Upload a PDF or DOCX resume. The portal extracts text and uses it as interview context.")

    uploaded = st.file_uploader("Upload Resume", type=["pdf", "docx"])

    if uploaded:
        if uploaded.name.lower().endswith((".pdf", ".docx")):
            file_type = uploaded.name.lower().split(".")[-1]
            text = extract_resume_text(uploaded.read(), file_type)

            st.session_state.resume_text = text[:12000]
            st.success("Resume loaded successfully.")
            st.write("### Extracted Resume Text")
            st.text_area("Preview", value=st.session_state.resume_text, height=300)
        else:
            st.error("Unsupported file type. Please upload a PDF or DOCX file.")


# ---------------------------------------------------------------------------
# Code analysis
# ---------------------------------------------------------------------------
def code_analysis_page():
    st.title("💻 Code Explainer")
    st.write("Upload or paste code and get a plain-English, step-by-step walkthrough of what it "
             "does and what output it produces — not a score. Good for understanding unfamiliar "
             "code or double-checking your own logic before an interview.")

    language = st.selectbox("Language (or leave on Auto-detect)",
                             ["auto", "python", "javascript", "java", "c++", "other"])

    tab_upload, tab_paste = st.tabs(["Upload File", "Paste Code"])
    code_text = ""

    with tab_upload:
        code_file = st.file_uploader(
            "Upload code file", type=["py", "js", "java", "cpp", "c", "txt"], key="code_file"
        )
        if code_file:
            code_text = code_file.read().decode("utf-8", errors="ignore")
            st.code(code_text[:3000], language=language if language != "auto" else None)

    with tab_paste:
        pasted = st.text_area("Paste your code here", height=250, key="code_paste")
        if pasted:
            code_text = pasted

    if st.button("Explain This Code", use_container_width=True):
        if not code_text.strip():
            st.error("Please upload or paste some code first.")
        else:
            with st.spinner("Reading through the code..."):
                result = explain_code(code_text, language)

            st.markdown('<div class="portal-card">', unsafe_allow_html=True)
            st.markdown(f"**Detected language:** {result['language']}")
            st.markdown("### Step-by-step explanation")
            st.write(result["explanation"])
            st.markdown("### Expected output / behavior")
            st.write(result["expected_output"])
            st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Communication practice
# ---------------------------------------------------------------------------
def communication_page():
    st.title("🗣 Communication Practice")

    st.markdown('<div class="portal-card">', unsafe_allow_html=True)
    st.caption(
        "⚠️ Honest limitation: this doesn't do live, continuous gesture/eye-contact AI "
        "tracking — that needs a persistent video pipeline and CV models that don't fit "
        "Streamlit's page-reload design. What you get here is a real, working stand-in: "
        "your camera confirms presence, and your pace/content is scored from your timed response."
    )
    st.markdown('</div>', unsafe_allow_html=True)

    if not st.session_state.comm_camera_on:
        st.write("Ready to practice? Start your camera to begin.")
        if st.button("🎥 Start Camera & Begin", use_container_width=True):
            st.session_state.comm_camera_on = True
            st.rerun()
        return

    mode = st.radio("What do you want to practice?",
                     ["Talk about my uploaded info", "AI-generated technical question"],
                     horizontal=True)

    cam_col, prompt_col = st.columns([1, 1.3])

    if mode == "Talk about my uploaded info":
        with cam_col:
            st.markdown("##### 🎥 Camera")
            snapshot = st.camera_input("Look at the camera, keep good posture, and speak clearly",
                                        label_visibility="collapsed")

        with prompt_col:
            info_file = st.file_uploader("Upload a PDF or DOCX (resume, bio, project summary, etc.)",
                                          type=["pdf", "docx"], key="comm_info_file")
            source_text = st.session_state.get("comm_source_text", "")
            if info_file:
                file_type = info_file.name.lower().split(".")[-1]
                source_text = extract_resume_text(info_file.read(), file_type)
                st.session_state.comm_source_text = source_text

            st.markdown('<div class="teleprompter-card">', unsafe_allow_html=True)
            st.markdown('<div class="tp-label">Read from / talk about this</div>', unsafe_allow_html=True)
            if source_text:
                st.markdown(f'<div class="tp-answer">{source_text[:1500]}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="tp-answer" style="color:#64748b;">Upload a file above — '
                             'its content will appear here for you to reference while looking at the camera.</div>',
                             unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("### Speak, then type what you said")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶ Start Speaking Timer", use_container_width=True):
                st.session_state.comm_start = time.time()
                st.success("Timer started — talk about your uploaded info, then type it below.")

        transcript = st.text_area("Your response / transcript", height=120, key="comm_transcript_info")

        with col2:
            if st.button("✅ Submit & Score", use_container_width=True, key="comm_submit_info"):
                if st.session_state.comm_start is None:
                    st.error("Click 'Start Speaking Timer' before submitting.")
                elif not source_text.strip():
                    st.error("Upload your info file first.")
                else:
                    elapsed = time.time() - st.session_state.comm_start
                    result = score_talk_about_info(source_text, transcript, elapsed, snapshot is not None)
                    save_communication_result(
                        st.session_state.user["id"],
                        result["pace_score"], result["presence_score"],
                        result["overall_score"], result["feedback"],
                    )
                    st.session_state.comm_start = None

                    st.markdown('<div class="portal-card">', unsafe_allow_html=True)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Pace Score", f"{result['pace_score']}/10")
                    c2.metric("Content Match", f"{result['content_score']}/10")
                    c3.metric("Overall", f"{result['overall_score']}/10")
                    st.write(result["feedback"])
                    st.markdown('</div>', unsafe_allow_html=True)

    else:  # AI-generated technical question
        with cam_col:
            st.markdown("##### 🎥 Camera")
            snapshot = st.camera_input("Look at the camera, keep good posture, and speak clearly",
                                        label_visibility="collapsed")

            role = st.text_input("Role", value="Software Engineer", key="comm_role")
            difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"], key="comm_diff")
            if st.button("🎲 Generate Question", use_container_width=True):
                with st.spinner("Generating..."):
                    qa = generate_question_with_answer(role, difficulty)
                st.session_state.comm_question = qa["question"] or "Explain a technical concept you know well."
                st.session_state.comm_model_answer = qa["answer"]

        question = st.session_state.get("comm_question", "")
        model_answer = st.session_state.get("comm_model_answer", "")

        with prompt_col:
            st.markdown('<div class="teleprompter-card">', unsafe_allow_html=True)
            if question:
                st.markdown('<div class="tp-label">Question</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="tp-question">{question}</div>', unsafe_allow_html=True)
                st.markdown('<div class="tp-label">Practice saying an answer like this</div>', unsafe_allow_html=True)
                if model_answer:
                    st.markdown(f'<div class="tp-answer">{model_answer}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="tp-answer" style="color:#64748b;">No model answer available '
                                 '(set OPENAI_API_KEY for one). Answer in your own words.</div>',
                                 unsafe_allow_html=True)
            else:
                st.markdown('<div class="tp-label">No question yet</div>', unsafe_allow_html=True)
                st.markdown('<div class="tp-answer" style="color:#64748b;">Click "Generate Question" on the left '
                             'to get a question and a model answer to practice reading while looking at the camera.'
                             '</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("### Speak your answer, then type what you said")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶ Start Speaking Timer", use_container_width=True, key="comm_start_tech"):
                st.session_state.comm_start = time.time()
                st.success("Timer started — answer out loud, then type it below.")

        transcript = st.text_area("Your response / transcript", height=120, key="comm_transcript_tech")

        with col2:
            if st.button("✅ Submit & Score", use_container_width=True, key="comm_submit_tech"):
                if st.session_state.comm_start is None:
                    st.error("Click 'Start Speaking Timer' before submitting.")
                elif not question:
                    st.error("Generate a question first.")
                else:
                    elapsed = time.time() - st.session_state.comm_start
                    delivery = score_communication(transcript, elapsed, snapshot is not None)
                    content = evaluate_against_expected(question, model_answer, transcript)
                    overall = round((delivery["overall_score"] * 0.4 + content["score"] * 0.6), 1)

                    save_communication_result(
                        st.session_state.user["id"],
                        delivery["pace_score"], delivery["presence_score"],
                        overall, content["feedback"],
                    )
                    st.session_state.comm_start = None

                    st.markdown('<div class="portal-card">', unsafe_allow_html=True)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Delivery (Pace)", f"{delivery['pace_score']}/10")
                    c2.metric("Answer Quality", f"{content['score']}/10")
                    c3.metric("Overall", f"{overall}/10")
                    st.write(content["feedback"])
                    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Stop Camera"):
        st.session_state.comm_camera_on = False
        st.rerun()


# ---------------------------------------------------------------------------
# Typing test
# ---------------------------------------------------------------------------
TIMED_TESTS = [("1:00 Test", 60), ("3:00 Test", 180), ("5:00 Test", 300)]
PAGE_TESTS = [("1 Page Test", 1), ("2 Page Test", 2)]


def typing_test_page():
    st.title("🏁 Typing Speed Racing")
    st.caption("Race against the clock — type the passage as fast and accurately as you can. "
               "A fresh passage is generated each time, so you won't see the same text twice in a row.")

    if "typing_passage" not in st.session_state:
        st.session_state.typing_passage = generate_typing_passage()
    if "typing_selected" not in st.session_state:
        st.session_state.typing_selected = None  # (label, kind, value)

    # ---- Test picker ----
    left, right = st.columns([1, 2])
    with left:
        st.markdown("#### Timed Tests")
        for label, secs in TIMED_TESTS:
            selected = st.session_state.typing_selected == ("timed", label)
            if st.button(f"{'✅ ' if selected else '▶ '}{label}", key=f"tt_{label}", use_container_width=True):
                st.session_state.typing_selected = ("timed", label, secs)
                st.rerun()

        st.markdown("#### Page Tests")
        for label, pages in PAGE_TESTS:
            selected = st.session_state.typing_selected == ("page", label)
            if st.button(f"{'✅ ' if selected else '▶ '}{label}", key=f"pt_{label}", use_container_width=True):
                st.session_state.typing_selected = ("page", label, pages)
                st.rerun()

        st.divider()
        can_start = st.session_state.typing_selected is not None and st.session_state.typing_start is None
        if st.button("🚀 Start Test", use_container_width=True, disabled=not can_start,
                     type="primary" if can_start else "secondary"):
            kind, label, value = st.session_state.typing_selected
            prev_passage = st.session_state.typing_passage
            if kind == "timed":
                st.session_state.typing_duration = value
                st.session_state.typing_passage = generate_typing_passage(avoid_text=prev_passage)
            else:
                st.session_state.typing_duration = 600
                base = generate_typing_passage(avoid_text=prev_passage)
                st.session_state.typing_passage = " ".join([base] * value)
            st.session_state.typing_duration_label = label
            st.session_state.typing_locked = False
            st.session_state.typing_start = time.time()
            st.rerun()

        if st.session_state.typing_selected and st.session_state.typing_start is None:
            st.caption(f"Selected: **{st.session_state.typing_selected[1]}** — click Start Test to begin.")

    with right:
        if st.session_state.typing_locked:
            st.markdown('<div class="portal-card">', unsafe_allow_html=True)
            st.markdown("### 🏅 Test Already Attempted")
            st.write("You have already participated in this typing speed test. "
                     "Multiple attempts are not permitted for this session.")
            last = get_user_typing_results(st.session_state.user["id"])
            if last:
                c1, c2 = st.columns(2)
                c1.metric("Your Speed", f"{last[0]['wpm']} WPM")
                c2.metric("Your Accuracy", f"{last[0]['accuracy']}%")
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button("Start a new test to try again"):
                st.session_state.typing_locked = False
                st.session_state.typing_start = None
                st.session_state.typing_selected = None
                st.rerun()
            return

        if st.session_state.typing_start is None:
            st.info("Pick a test on the left to begin.")
            return

        elapsed_so_far = time.time() - st.session_state.typing_start
        remaining = max(0, st.session_state.typing_duration - elapsed_so_far)

        st.markdown(f"**{st.session_state.typing_duration_label}** — "
                     f"⏱ time remaining: **{int(remaining)}s**")

        def _enforce_typing():
            """Runs on every keystroke (text_input fires live, unlike
            text_area which only updates on blur). If the latest character
            doesn't match the passage at that position, the extra character(s)
            are trimmed back off — so you can't advance past a mistake until
            you fix it."""
            ref = st.session_state.typing_passage
            typed_now = st.session_state.get("typed_input", "")
            mismatch_idx = None
            for i in range(min(len(typed_now), len(ref))):
                if typed_now[i] != ref[i]:
                    mismatch_idx = i
                    break
            if mismatch_idx is not None and len(typed_now) > mismatch_idx + 1:
                st.session_state.typed_input = typed_now[: mismatch_idx + 1]

        # Typing.com-style: the full passage renders as a wrapping paragraph
        # with completed words highlighted green/red and a blue cursor at the
        # current letter. A slim input sits directly under it (borders
        # touching, no gap) to capture keystrokes live on every character.
        typed_so_far = st.session_state.get("typed_input", "")
        diff_html = diff_typing_html(st.session_state.typing_passage, typed_so_far)
        st.markdown(f'<div class="typing-paragraph" id="typing-paragraph-box">{diff_html}</div>'
                     '<img src="x" style="display:none" onerror="'
                     'var box=document.getElementById(\'typing-paragraph-box\');'
                     'var cur=document.getElementById(\'typing-cursor\');'
                     'if(box&&cur){box.scrollTop = cur.offsetTop - box.clientHeight/2;}'
                     '">', unsafe_allow_html=True)
        typed = st.text_input("Type here", key="typed_input", label_visibility="collapsed",
                               placeholder="Click here and start typing...", on_change=_enforce_typing)

        col1, col2 = st.columns(2)
        with col1:
            submit = st.button("Submit", use_container_width=True)
        with col2:
            if st.button("Cancel Test", use_container_width=True):
                st.session_state.typing_start = None
                st.rerun()

        if remaining <= 0 and not submit:
            st.warning("Time's up! Click Submit to record your result.")

        if submit:
            capped_elapsed = min(time.time() - st.session_state.typing_start, st.session_state.typing_duration)
            result = score_typing_test(st.session_state.typing_passage, typed, capped_elapsed)
            save_typing_result(st.session_state.user["id"], result["wpm"], result["accuracy"], capped_elapsed)
            st.session_state.typing_start = None
            st.session_state.typing_locked = True
            st.rerun()


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
def sidebar():
    with st.sidebar:
        st.write(f"👤 **{st.session_state.user['username']}**")
        st.divider()
        if st.button("📊 Dashboard", use_container_width=True):
            go("dashboard")
        if st.button("🆕 New Interview", use_container_width=True):
            go("new_interview")
        if st.button("📄 Resume Analyzer", use_container_width=True):
            go("resume")
        if st.button("💻 Code Analysis", use_container_width=True):
            go("code_analysis")
        if st.button("🗣 Communication Practice", use_container_width=True):
            go("communication")
        if st.button("⌨️ Typing Test", use_container_width=True):
            go("typing_test")
        st.divider()
        if st.button("Logout", use_container_width=True):
            st.session_state.user = None
            go("auth")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
if st.session_state.user is None:
    auth_page()
else:
    sidebar()
    page = st.session_state.page
    if page == "dashboard":
        dashboard()
    elif page == "new_interview":
        new_interview()
    elif page == "interview":
        interview_page()
    elif page == "finish_interview":
        finish_interview()
    elif page == "resume":
        resume_page()
    elif page == "code_analysis":
        code_analysis_page()
    elif page == "communication":
        communication_page()
    elif page == "typing_test":
        typing_test_page()
    else:
        dashboard()