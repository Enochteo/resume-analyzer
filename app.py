import os
import re
import openai
from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
import pdfplumber
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from openai import OpenAI
from collections import Counter
import difflib
from flask_login import login_user, logout_user, login_required, LoginManager
from models import db, User
from flask_migrate import Migrate


app = Flask(__name__)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///app.db'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")  

load_dotenv()
#print("Loaded API Key:", os.getenv("OPENAI_API_KEY"))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        password = request.form.get("password")

        if User.query.filter_by(email=email).first():
            flash("Email already registered")
            return redirect(url_for("login"))
        new_user = User(full_name=full_name, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("Account successfully created")
        #login_user(new_user)
        return redirect(url_for("login"))
    else:
        return render_template("auth/register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("index"))
        else:
            return render_template("auth/login.html", error="Invalid credentials")
    return render_template("auth/login.html")

@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify({"status": "SmartCV API is running", "version": "1.0"}), 200


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))

def extract_text_from_pdf(filepath):
    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text.strip()

def extract_score_from_feedback(feedback):
    match = re.search(r"(?:Match\s*Score|Score)\D*?(\d{1,3})", feedback)
    return int(match.group(1)) if match else 0


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    resume_text = ""
    if request.method == "POST":
        uploaded_file = request.files.get("resume")
        if uploaded_file and uploaded_file.filename.endswith(".pdf"):
            filename = secure_filename(uploaded_file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            uploaded_file.save(filepath)
            resume_text = extract_text_from_pdf(filepath)
            job_description = request.form.get("job_description", "")
            feedback = get_resume_feedback(resume_text, job_description)
            gpt_score = extract_score_from_feedback(feedback)
            ats_score = calculate_ats_score(resume_text, job_description)
            return render_template("results.html", resume=resume_text, feedback=feedback, gpt_score=gpt_score, ats_score=ats_score, show_back_button=True)
    return render_template("index.html")

def get_resume_feedback(resume_text, job_description):
    prompt = f"""You are an expert tech recruiter. Analyze this resume and compare it to the job description:
    - Score the resume from 0 to 100 based on how well it fits the job.
    - List the top missing keywords 
    - List the key technical skills missing.
    - Suggest 3 improvements to increase match quality.
    Emphasize clarity and impact of bullet points
    Tailoring response to the job description given
    Resume:
    {resume_text}
    Job Description:
    {job_description}
"""
    
    response = client.chat.completions.create(
        model = "gpt-3.5-turbo",
        messages = [{"role": "user", "content": prompt}],
        temperature = 0.7,
        max_tokens = 700
    )
    print("RAW RESPONSE:", response)
    return response.choices[0].message.content.strip()

@app.route("/rewrite", methods=["POST"])
def rewrite():
    bullet = request.form.get("bullet")
    prompt = f"""
You are a career optimization expert helping users rewrite their resumes to match job descriptions.

Rewrite the resume below with the following goals:
- Emphasize keywords from the job description
- Improve clarity, action, and measurable impact
- Keep formatting simple and professional
- Remove irrelevant parts

Resume:
{resume_text}

Job Description:
{job_description}
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=150
    )
    rewritten = response.choices[0].message.content.strip()
    return jsonify({"rewritten": rewritten})

def calculate_ats_score(resume_text, job_description):
    score = 0
    max_score = 100

    # Keyword Overlap (40 pts)
    job_keywords = get_job_keywords(job_description)
    resume_words = set(re.findall(r'\b\w+\b', resume_text.lower()))
    overlap = sum(1 for word in job_keywords if word in resume_words)
    keyword_score = min(int((overlap / len(job_keywords)) * 40), 40)
    score += keyword_score

    # Resume Sections (30 pts)
    sections = ["experience", "education", "skills", "projects"]
    section_score = sum(1 for sec in sections if sec in resume_text.lower()) * 7.5
    score += section_score

    # Contact Info (15 pts)
    has_email = bool(re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", resume_text))
    has_phone = bool(re.search(r"\+?\d[\d -]{8,}\d", resume_text))
    score += 7 if has_email else 0
    score += 8 if has_phone else 0

    # Resume Length (15 pts)
    word_count = len(resume_text.split())
    if 300 <= word_count <= 900:
        score += 15

    return min(score, max_score)


@app.route("/fixit", methods=["GET", "POST"])
def fixit():
    return render_template("fixit.html", show_back_button=True)


@app.route("/rewrite_resume_from_feedback", methods=["POST"])
def rewrite_resume_from_feedback():
    resume = request.form.get("resume", "")
    job_description = request.form.get("job_description", "")

    prompt = f"""You are a professional resume writer. Based on the job description below, rewrite the provided resume to maximize alignment with the job. Maintain professionalism, improve formatting, enhance clarity, and emphasize relevant achievements.
    
    Job Description:
    {job_description}

    Original Resume:
    {resume}

    Rewritten Resume:"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1000
    )

    rewritten = response.choices[0].message.content.strip()

    # Split into lines (by sentence or bullet point)
    original_lines = [line.strip() for line in resume.split("\n") if line.strip()]
    rewritten_lines = [line.strip() for line in rewritten.split("\n") if line.strip()]

    # Align similar-length content
    rewrites = []
    matcher = difflib.SequenceMatcher(None, original_lines, rewritten_lines)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ["replace", "equal"]:
            for i, j in zip(range(i1, i2), range(j1, j2)):
                rewrites.append((original_lines[i], rewritten_lines[j]))
        elif tag == "delete":
            for i in range(i1, i2):
                rewrites.append((original_lines[i], ""))
        elif tag == "insert":
            for j in range(j1, j2):
                rewrites.append(("", rewritten_lines[j]))

    return render_template("rewrite_resume_based_on_feedback.html", rewrites=rewrites, show_back_button=True)

@app.route("/rewrite_resume_auto", methods=["POST"])
@login_required
def rewrite_resume_auto():
    resume = request.form.get("resume", "")
    job_description = request.form.get("job_description", "")

    prompt = f"""
You are a professional resume editor and recruiter. Rewrite this resume to:
- Increase the match score with the job description
- Use strong action verbs and measurable results
- Add keywords that align with the job
- Improve formatting, clarity, and impact

Job Description:
{job_description}

Resume:
{resume}

After rewriting, give an estimated match score (0-100) based on the job description.
 
Output Format:
Rewritten Resume:
<your content>

Match Score: <number>
"""


    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=1200
    )

    rewritten_resume = response.choices[0].message.content.strip()

    # Optionally re-score the new resume with your existing feedback function
    feedback = get_resume_feedback(rewritten_resume, job_description)
    score = extract_score_from_feedback(feedback)

    return render_template("rewrite_result.html", original=resume, rewritten=rewritten_resume, score=score, feedback=feedback, show_back_button=True)

@app.route("/keyword_heatmap", methods=["POST"])
@login_required
def keyword_heatmap():
    resume = request.form.get("resume", "")
    job_description = request.form.get("job_description", "")

    job_keywords = get_job_keywords(job_description)
    data = keyword_overlap(job_keywords, resume)

    # Sort top 20 keywords
    data = sorted(data, key=lambda x: x[1], reverse=True)[:20]
    words, counts = zip(*data)

    return render_template("keyword_heatmap.html", words=words, counts=counts, show_back_button=True)

def get_job_keywords(text):
    stopwords = {"and", "or", "with", "a", "an", "the", "in", "for", "of", "to", "on", "at", "by", "is"}
    words = re.findall(r'\b\w+\b', text.lower())
    keywords = [w for w in words if w not in stopwords and len(w) > 2]
    return Counter(keywords)

def keyword_overlap(job_keywords, resume_text):
    resume_words = re.findall(r'\b\w+\b', resume_text.lower())
    resume_counter = Counter(resume_words)

    data = []
    for word, _ in job_keywords.items():
        resume_count = resume_counter.get(word, 0)
        data.append((word, resume_count))
    return data

@app.route("/api/score", methods=["POST"])
def api_score():
    data = request.get_json()
    resume = data.get("resume", "")
    job_description = data.get("job_description", "")

    feedback = get_resume_feedback(resume, job_description)
    gpt_score = extract_score_from_feedback(feedback)
    ats_score = calculate_ats_score(resume, job_description)

    return jsonify({
        "gpt_match_score": gpt_score,
        "ats_friendly_score": ats_score,
        "feedback": feedback
    }), 200

db.init_app(app)
migrate = Migrate(app, db)
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, host="localhost", port=5050)
