import streamlit as st
import json
import re
import io
from html import escape

from google import genai
from pypdf import PdfReader
from docx import Document


# --------------------------------------------------
# APP CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Voice2Prep | AI Interview Coach",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

MODEL = "gemini-3.5-flash-lite"


# --------------------------------------------------
# GEMINI CONNECTION
# --------------------------------------------------

def get_client():
    api_key = st.secrets.get("GEMINI_API_KEY")

    if not api_key:
        st.error(
            "Gemini API key not found. Add GEMINI_API_KEY "
            "to your .streamlit/secrets.toml file."
        )
        st.stop()

    return genai.Client(api_key=api_key)


def ask_gemini(prompt):
    client = get_client()

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    return response.text


def extract_json(text):
    """Extract JSON even if Gemini wraps it in Markdown."""

    text = text.strip()
    text = re.sub(r"```json|```", "", text).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("Could not find valid JSON in the AI response.")

    return json.loads(text[start:end + 1])


# --------------------------------------------------
# RESUME EXTRACTION
# --------------------------------------------------

def extract_resume_text(uploaded_file):
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    elif file_name.endswith(".docx"):
        document = Document(uploaded_file)
        return "\n".join(
            paragraph.text for paragraph in document.paragraphs
        )

    elif file_name.endswith(".txt"):
        return uploaded_file.getvalue().decode("utf-8", errors="ignore")

    return ""


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

defaults = {
    "analysis": None,
    "questions": [],
    "question_index": 0,
    "active_question": "",
    "is_followup": False,
    "evaluation": None,
    "history": [],
    "interview_finished": False,
    "role": "",
    "resume_text": "",
    "interview_started": False
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_app():
    for key, value in defaults.items():
        st.session_state[key] = value


def move_to_next_question():
    st.session_state.evaluation = None
    st.session_state.is_followup = False

    next_index = st.session_state.question_index + 1

    if next_index >= len(st.session_state.questions):
        st.session_state.interview_finished = True
        st.session_state.active_question = ""
    else:
        st.session_state.question_index = next_index
        st.session_state.active_question = (
            st.session_state.questions[next_index]["question"]
        )


# --------------------------------------------------
# DESIGN / CSS
# --------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

    :root {
        --navy: #081225;
        --panel: #101e36;
        --blue: #3987ff;
        --cyan: #55d6ed;
        --text: #edf4ff;
        --muted: #9aabc5;
    }

    .stApp {
        background:
            radial-gradient(circle at 80% 0%, #132b50 0%, transparent 35%),
            linear-gradient(145deg, #081225, #0b1427 55%, #101d35);
        color: var(--text);
        font-family: 'DM Sans', sans-serif;
    }

    h1, h2, h3 {
        font-family: 'Space Grotesk', sans-serif !important;
        color: #f4f8ff !important;
    }

    p, label, li {
        color: #d1dced;
    }

    [data-testid="stSidebar"] {
        background: #0a162a;
        border-right: 1px solid rgba(130, 170, 220, 0.15);
    }

    .block-container {
        max-width: 1150px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .brand {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.65rem;
        font-weight: 700;
        letter-spacing: -1.5px;
        color: #ffffff;
        margin-bottom: 0;
    }

    .brand span {
        color: #55d6ed;
    }

    .tagline {
        color: #9eb4d2;
        font-size: 1.05rem;
        margin-top: 4px;
    }

    .hero {
        background: linear-gradient(
            120deg,
            rgba(28, 65, 119, 0.65),
            rgba(15, 34, 62, 0.88)
        );
        border: 1px solid rgba(100, 170, 255, 0.25);
        border-radius: 20px;
        padding: 30px;
        margin: 22px 0;
    }

    .hero-label {
        color: #63d9f0;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 2px;
    }

    .hero h1 {
        font-size: 2.4rem;
        margin: 12px 0 8px;
    }

    .hero p {
        color: #c3d3e9;
        font-size: 1rem;
        margin-bottom: 0;
    }

    .wave {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 5px;
        height: 65px;
        margin-top: 18px;
    }

    .wave span {
        width: 5px;
        border-radius: 10px;
        background: linear-gradient(
            180deg,
            #61e2f5,
            #3987ff
        );
        display: block;
        animation: wave 1.2s ease-in-out infinite;
    }

    .wave span:nth-child(1) { height: 16px; animation-delay: .1s; }
    .wave span:nth-child(2) { height: 30px; animation-delay: .2s; }
    .wave span:nth-child(3) { height: 44px; animation-delay: .3s; }
    .wave span:nth-child(4) { height: 25px; animation-delay: .4s; }
    .wave span:nth-child(5) { height: 55px; animation-delay: .5s; }
    .wave span:nth-child(6) { height: 35px; animation-delay: .6s; }
    .wave span:nth-child(7) { height: 48px; animation-delay: .7s; }
    .wave span:nth-child(8) { height: 22px; animation-delay: .8s; }
    .wave span:nth-child(9) { height: 40px; animation-delay: .9s; }
    .wave span:nth-child(10) { height: 17px; animation-delay: 1s; }

    @keyframes wave {
        0%, 100% { transform: scaleY(.65); opacity: .7; }
        50% { transform: scaleY(1); opacity: 1; }
    }

    .section-label {
        color: #61d8ef;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 1.5px;
        margin: 25px 0 12px;
    }

    .panel {
        background: rgba(17, 32, 56, 0.85);
        border: 1px solid rgba(130, 170, 220, 0.17);
        border-radius: 16px;
        padding: 22px;
        margin: 12px 0;
    }

    .question-card {
        background: linear-gradient(
            135deg,
            rgba(30, 69, 121, 0.65),
            rgba(16, 32, 57, 0.95)
        );
        border: 1px solid rgba(85, 214, 237, 0.3);
        border-radius: 18px;
        padding: 25px;
        margin: 12px 0 20px;
    }

    .question-number {
        color: #60d9ef;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 1.5px;
    }

    .question-text {
        color: #ffffff;
        font-size: 1.35rem;
        font-weight: 600;
        line-height: 1.5;
        margin-top: 12px;
    }

    .chat-note {
        background: rgba(45, 115, 190, 0.12);
        border-left: 3px solid #55d6ed;
        padding: 12px 15px;
        border-radius: 7px;
        color: #c8d9ed;
        font-size: 0.88rem;
        margin: 12px 0;
    }

    .metric-card {
        background: rgba(18, 35, 61, 0.9);
        border: 1px solid rgba(120, 165, 220, 0.2);
        border-radius: 14px;
        padding: 18px;
        text-align: center;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #60d9ef;
    }

    .metric-label {
        color: #a9bad2;
        font-size: 0.82rem;
    }

    .stButton > button {
        border-radius: 10px;
        border: 1px solid rgba(90, 180, 255, 0.35);
        background: linear-gradient(110deg, #2469d8, #258dbb);
        color: white;
        font-weight: 600;
        min-height: 43px;
    }

    .stButton > button:hover {
        border-color: #65e2f5;
        color: white;
        background: linear-gradient(110deg, #2d7cf0, #26a5c9);
    }

    .stTextInput input,
    .stTextArea textarea {
        background: #101f37 !important;
        color: #f3f7ff !important;
        border: 1px solid #304968 !important;
        border-radius: 10px !important;
    }

    [data-testid="stFileUploader"] {
        background: rgba(17, 32, 56, 0.7);
        border: 1px dashed #47749e;
        border-radius: 12px;
        padding: 12px;
    }

    .stProgress > div > div > div {
        background: linear-gradient(90deg, #3987ff, #55d6ed);
    }

    footer {
        visibility: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown(
    """
    <div>
        <div class="brand">Voice2<span>Prep</span></div>
        <div class="tagline">
            Speak. Practice. Get Hired.
        </div>
    </div>

    <div class="hero">
        <div class="hero-label">YOUR PERSONAL AI INTERVIEW COACH</div>
        <h1>Turn your preparation into confidence.</h1>
        <p>
            Understand your skill gaps, practice personalized interview
            questions, and improve your answers through AI-powered feedback.
        </p>
        <div class="wave">
            <span></span><span></span><span></span><span></span><span></span>
            <span></span><span></span><span></span><span></span><span></span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.markdown("## 🎙️ Voice2Prep")
    st.caption("Your interview preparation journey")

    st.divider()

    st.markdown("### Your progress")

    steps = [
        "01  Profile & Resume",
        "02  Skill Gap Analysis",
        "03  Interview Questions",
        "04  Mock Interview",
        "05  Performance Review"
    ]

    for step in steps:
        st.markdown(f"- {step}")

    st.divider()

    if st.session_state.analysis:
        st.success("Profile analyzed")

    if st.session_state.interview_started:
        st.info("Mock interview started")

    if st.button("↻ Start Over", use_container_width=True):
        reset_app()
        st.rerun()

    st.divider()

    st.caption("Powered by Gemini AI")
    st.caption("Voice input: Wispr Flow")


# --------------------------------------------------
# STEP 1: ROLE AND RESUME
# --------------------------------------------------

st.markdown(
    '<div class="section-label">01 / YOUR INTERVIEW PROFILE</div>',
    unsafe_allow_html=True
)

st.markdown("### Tell us what role you're preparing for")

st.write(
    "Choose your target role and share your resume. "
    "Voice2Prep will personalize your preparation."
)

role = st.text_input(
    "Target job role",
    value=st.session_state.role,
    placeholder="e.g. AI Engineer, Data Analyst, Software Engineer",
    key="role_input"
)

uploaded_file = st.file_uploader(
    "Upload your resume (PDF, DOCX or TXT)",
    type=["pdf", "docx", "txt"],
    key="resume_upload"
)

pasted_resume = st.text_area(
    "Or paste your resume text here",
    value=st.session_state.resume_text,
    height=180,
    placeholder="Paste your resume content here..."
)

st.markdown(
    """
    <div class="chat-note">
        <b>🎙️ Voice-powered preparation:</b>
        Use Wispr Flow to dictate your resume details or answers
        directly into the text boxes. No separate recording is needed.
    </div>
    """,
    unsafe_allow_html=True
)

resume_text = pasted_resume.strip()

if uploaded_file is not None:
    try:
        extracted_text = extract_resume_text(uploaded_file)

        if extracted_text.strip():
            resume_text = extracted_text.strip()
            st.success("Resume uploaded and text extracted successfully.")
        else:
            st.warning(
                "No readable text found. If this is a scanned PDF, "
                "please paste the resume text instead."
            )

    except Exception as error:
        st.error(f"Could not read the uploaded resume: {error}")


if st.button(
    "✨ Analyze My Profile",
    type="primary",
    use_container_width=True
):
    if not role.strip():
        st.warning("Please enter your target job role.")

    elif not resume_text.strip():
        st.warning("Please upload or paste your resume.")

    else:
        st.session_state.role = role.strip()
        st.session_state.resume_text = resume_text

        prompt = f"""
        You are an expert technical career coach and interview preparation
        specialist.

        Analyze this candidate's resume for the target role:
        {role}

        RESUME:
        {resume_text}

        Important:
        - Do not ask for a job description.
        - Use general industry expectations for this role.
        - Do not invent experience or skills that are absent from the resume.
        - Be supportive but honest.
        - Focus on actionable preparation.

        Return ONLY valid JSON in this format:

        {{
            "readiness_score": 65,
            "profile_summary": "Short candidate profile summary",
            "strengths": [
                "Strength 1",
                "Strength 2",
                "Strength 3"
            ],
            "skill_gaps": [
                {{
                    "skill": "Skill name",
                    "importance": "High",
                    "reason": "Why this skill matters for the role"
                }}
            ],
            "preparation_plan": [
                "Action 1",
                "Action 2",
                "Action 3"
            ]
        }}

        readiness_score must be an integer from 0 to 100.
        importance must be High, Medium, or Low.
        """

        try:
            with st.spinner("Analyzing your profile with AI..."):
                result = ask_gemini(prompt)
                analysis = extract_json(result)

            st.session_state.analysis = analysis
            st.session_state.questions = []
            st.session_state.history = []
            st.session_state.question_index = 0
            st.session_state.evaluation = None
            st.session_state.interview_started = False
            st.session_state.interview_finished = False

            st.success("Your personalized profile analysis is ready!")
            st.rerun()

        except Exception as error:
            st.error(f"Profile analysis failed: {error}")


# --------------------------------------------------
# STEP 2: SKILL GAP ANALYSIS
# --------------------------------------------------

if st.session_state.analysis:

    analysis = st.session_state.analysis

    st.markdown("---")
    st.markdown(
        '<div class="section-label">02 / YOUR READINESS REPORT</div>',
        unsafe_allow_html=True
    )

    st.markdown("### Your interview readiness")

    score = int(analysis.get("readiness_score", 0))
    score = max(0, min(score, 100))

    metric_col1, metric_col2 = st.columns([1, 2])

    with metric_col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">READINESS SCORE</div>
                <div class="metric-value">{score}%</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with metric_col2:
        st.markdown("#### Candidate overview")
        st.write(analysis.get("profile_summary", "No summary available."))
        st.progress(score / 100)

    st.markdown("### Your strengths")

    strengths = analysis.get("strengths", [])

    if strengths:
        for strength in strengths:
            st.markdown(f"- ✅ {strength}")
    else:
        st.info("No strengths were returned.")

    st.markdown("### Skills to strengthen")

    skill_gaps = analysis.get("skill_gaps", [])

    if skill_gaps:
        for gap in skill_gaps:
            with st.expander(
                f"{gap.get('skill', 'Skill')} — "
                f"{gap.get('importance', 'Medium')} priority"
            ):
                st.write(gap.get("reason", ""))
    else:
        st.info("No skill gaps were returned.")

    st.markdown("### Your preparation plan")

    for index, item in enumerate(
        analysis.get("preparation_plan", []), start=1
    ):
        st.markdown(f"**{index}.** {item}")


    # --------------------------------------------------
    # STEP 3: GENERATE QUESTIONS
    # --------------------------------------------------

    st.markdown("---")
    st.markdown(
        '<div class="section-label">03 / PERSONALIZED QUESTION SET</div>',
        unsafe_allow_html=True
    )

    st.markdown("### Questions selected for your role")

    st.write(
        "Your questions are generated using your target role, "
        "resume, and common industry interview expectations."
    )

    if not st.session_state.questions:

        if st.button(
            "🎯 Generate My 10 Interview Questions",
            type="primary",
            use_container_width=True
        ):

            question_prompt = f"""
            You are an experienced interviewer.

            Generate exactly 10 personalized interview questions for:

            TARGET ROLE: {st.session_state.role}

            CANDIDATE RESUME:
            {st.session_state.resume_text}

            PROFILE ANALYSIS:
            {json.dumps(analysis)}

            Requirements:
            - 3 beginner questions
            - 4 intermediate questions
            - 3 advanced questions
            - Questions must be relevant to the target role.
            - Include questions based on the candidate's actual projects,
              skills and experience where relevant.
            - Do not assume skills that are not in the resume.
            - Include a mixture of technical, practical and
              experience-based questions.

            Return ONLY valid JSON:

            {{
                "questions": [
                    {{
                        "question": "Question text",
                        "difficulty": "Beginner",
                        "topic": "Topic name"
                    }}
                ]
            }}
            """

            try:
                with st.spinner("Creating your personalized questions..."):
                    result = ask_gemini(question_prompt)
                    question_data = extract_json(result)

                questions = question_data.get("questions", [])

                if len(questions) != 10:
                    st.warning(
                        f"AI returned {len(questions)} questions "
                        "instead of 10. You can still use them."
                    )

                if not questions:
                    raise ValueError("No questions were generated.")

                st.session_state.questions = questions
                st.success("Your interview questions are ready!")
                st.rerun()

            except Exception as error:
                st.error(f"Question generation failed: {error}")

    else:

        for index, question in enumerate(
            st.session_state.questions, start=1
        ):
            difficulty = question.get("difficulty", "General")
            topic = question.get("topic", "General")

            st.markdown(
                f"""
                <div class="panel">
                    <div style="color:#61d8ef;font-size:0.75rem;">
                        QUESTION {index} · {escape(str(difficulty)).upper()}
                    </div>
                    <div style="font-size:1rem;font-weight:600;
                                color:#f3f7ff;margin-top:8px;">
                        {escape(str(question.get("question", "")))}
                    </div>
                    <div style="color:#9aabc5;font-size:0.8rem;
                                margin-top:8px;">
                        Topic: {escape(str(topic))}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


        # --------------------------------------------------
        # STEP 4: MOCK INTERVIEW
        # --------------------------------------------------

        st.markdown("---")
        st.markdown(
            '<div class="section-label">04 / CONVERSATIONAL MOCK INTERVIEW</div>',
            unsafe_allow_html=True
        )

        st.markdown("### Practice like it's a real interview")

        st.write(
            "Answer one question at a time. Use Wispr Flow to dictate "
            "your answer, then get personalized feedback from AI."
        )

        if not st.session_state.interview_started:

            st.markdown(
                """
                <div class="panel">
                    <h3>Ready for your practice interview?</h3>
                    <p>
                        Your AI interviewer will ask one question at a time.
                        You can evaluate your answer, receive feedback,
                        and answer follow-up questions.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button(
                "▶ Start Mock Interview",
                type="primary",
                use_container_width=True
            ):
                st.session_state.interview_started = True
                st.session_state.question_index = 0
                st.session_state.active_question = (
                    st.session_state.questions[0]["question"]
                )
                st.session_state.interview_finished = False
                st.session_state.evaluation = None
                st.session_state.history = []
                st.rerun()

        elif st.session_state.interview_finished:

            st.success("🎉 You have completed your mock interview!")

            total = len(st.session_state.history)

            if total:
                average_score = sum(
                    item["score"] for item in st.session_state.history
                ) / total
            else:
                average_score = 0

            result_col1, result_col2 = st.columns(2)

            with result_col1:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">ANSWERS EVALUATED</div>
                        <div class="metric-value">{total}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with result_col2:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">AVERAGE SCORE</div>
                        <div class="metric-value">{average_score:.1f}/10</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown("### Your interview performance")

            for index, item in enumerate(
                st.session_state.history, start=1
            ):
                with st.expander(f"Question {index}: {item['question']}"):
                    st.write("**Your answer:**")
                    st.write(item["answer"])
                    st.write(f"**Score:** {item['score']}/10")
                    st.write("**Feedback:**")
                    st.write(item["feedback"])

            if st.button("↻ Practice Again", use_container_width=True):
                st.session_state.interview_started = False
                st.session_state.interview_finished = False
                st.session_state.question_index = 0
                st.session_state.active_question = ""
                st.session_state.history = []
                st.session_state.evaluation = None
                st.rerun()

        else:

            current_number = st.session_state.question_index + 1
            total_questions = len(st.session_state.questions)

            st.progress(
                min(current_number / total_questions, 1.0)
            )

            if st.session_state.is_followup:
                question_label = "FOLLOW-UP QUESTION"
            else:
                question_label = (
                    f"QUESTION {current_number} OF {total_questions}"
                )

            st.markdown(
                f"""
                <div class="question-card">
                    <div class="question-number">{question_label}</div>
                    <div class="question-text">
                        {escape(st.session_state.active_question)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            answer_key = (
                f"answer_{current_number}_"
                f"{'followup' if st.session_state.is_followup else 'main'}"
            )

            answer = st.text_area(
                "Your answer",
                key=answer_key,
                height=160,
                placeholder=(
                    "Start typing or use Wispr Flow to dictate "
                    "your answer here..."
                )
            )

            st.markdown(
                """
                <div class="chat-note">
                    <b>🎙️ Your voice, your answer.</b>
                    Use Wispr Flow to speak your response into this
                    text box. When you're finished, choose
                    <b>Evaluate My Answer</b>.
                </div>
                """,
                unsafe_allow_html=True
            )

            evaluate_col, next_col = st.columns(2)

            with evaluate_col:
                evaluate_clicked = st.button(
                    "✨ Evaluate My Answer",
                    type="primary",
                    use_container_width=True
                )

            with next_col:
                next_clicked = st.button(
                    "Next Question →",
                    use_container_width=True
                )


            # --------------------------------------------------
            # ANSWER EVALUATION
            # --------------------------------------------------

            if evaluate_clicked:

                if not answer.strip():
                    st.warning("Please enter your answer first.")

                else:

                    evaluation_prompt = f"""
                    You are a fair, supportive and technically accurate
                    interview evaluator.

                    TARGET ROLE: {st.session_state.role}

                    QUESTION:
                    {st.session_state.active_question}

                    CANDIDATE ANSWER:
                    {answer}

                    Evaluate the answer based on:
                    1. Accuracy
                    2. Technical depth
                    3. Clarity
                    4. Relevance to the question

                    Be constructive. Do not reward length alone.
                    Do not invent facts about the candidate.

                    Return ONLY valid JSON:

                    {{
                        "score": 7,
                        "strengths": [
                            "Strength 1",
                            "Strength 2"
                        ],
                        "missing_points": [
                            "Missing concept 1",
                            "Missing concept 2"
                        ],
                        "feedback": "Clear and helpful feedback",
                        "improved_answer": "A stronger example answer",
                        "followup_question": "A relevant follow-up question"
                    }}

                    Score must be an integer from 0 to 10.
                    If no follow-up is useful, return an empty string.
                    """

                    try:
                        with st.spinner("Evaluating your answer..."):
                            result = ask_gemini(evaluation_prompt)
                            evaluation = extract_json(result)

                        score = max(
                            0,
                            min(int(evaluation.get("score", 0)), 10)
                        )

                        evaluation["score"] = score
                        st.session_state.evaluation = evaluation

                        st.session_state.history.append({
                            "question": st.session_state.active_question,
                            "answer": answer.strip(),
                            "score": score,
                            "feedback": evaluation.get("feedback", "")
                        })

                        st.rerun()

                    except Exception as error:
                        st.error(f"Answer evaluation failed: {error}")


            # --------------------------------------------------
            # DISPLAY EVALUATION
            # --------------------------------------------------

            if st.session_state.evaluation:

                evaluation = st.session_state.evaluation

                st.markdown("---")
                st.markdown("### Your AI feedback")

                score = evaluation.get("score", 0)

                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">YOUR ANSWER SCORE</div>
                        <div class="metric-value">{score}/10</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown("#### What you did well")

                for item in evaluation.get("strengths", []):
                    st.markdown(f"- ✅ {item}")

                st.markdown("#### What you can improve")

                for item in evaluation.get("missing_points", []):
                    st.markdown(f"- 📌 {item}")

                st.markdown("#### Interviewer feedback")
                st.write(evaluation.get("feedback", ""))

                with st.expander("💡 View an improved sample answer"):
                    st.write(
                        evaluation.get("improved_answer", "")
                    )

                followup = evaluation.get("followup_question", "")

                if followup and not st.session_state.is_followup:
                    st.info(
                        "Your interviewer has a follow-up question "
                        "based on your answer."
                    )

                    if st.button(
                        "Answer Follow-up Question →",
                        type="primary",
                        use_container_width=True
                    ):
                        st.session_state.active_question = followup
                        st.session_state.is_followup = True
                        st.session_state.evaluation = None
                        st.rerun()

                else:
                    if st.button(
                        "Continue to Next Question →",
                        type="primary",
                        use_container_width=True
                    ):
                        move_to_next_question()
                        st.rerun()


            # --------------------------------------------------
            # SKIP QUESTION
            # --------------------------------------------------

            if next_clicked:

                if st.session_state.is_followup:
                    move_to_next_question()

                else:
                    move_to_next_question()

                st.rerun()


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.markdown(
    """
    <br><br>
    <div style="
        text-align:center;
        border-top:1px solid rgba(130,170,220,0.15);
        padding-top:20px;
        color:#8297b5;
        font-size:0.85rem;
    ">
        <b style="color:#55d6ed;">Voice2Prep</b>
        · Speak. Practice. Get Hired.
        <br>
        Your AI-powered interview preparation companion.
    </div>
    """,
    unsafe_allow_html=True
)