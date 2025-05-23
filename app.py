import os
import re
import openai
from flask import Flask, render_template, request, redirect
import pdfplumber
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from openai import OpenAI
from flask import jsonify
from collections import Counter
import difflib
from flask import session, url_for
from flask import jsonify, request




app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.secret_key = os.getenv("SECRET_KEY", "changeme")  
VALID_USERNAME = os.getenv("APP_USERNAME")
VALID_PASSWORD = os.getenv("APP_PASSWORD")

load_dotenv()
print("Loaded API Key:", os.getenv("OPENAI_API_KEY"))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == VALID_USERNAME and password == VALID_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify({"status": "SmartCV API is running 🚀", "version": "1.0"}), 200

@app.route("/api/score", methods=["POST"])
def api_score():
    data = request.get_json()
    resume = data.get("resume", "")
    job_description = data.get("job_description", "")

    feedback = get_resume_feedback(resume, job_description)
    score = extract_score_from_feedback(feedback)

    return jsonify({
        "score": score,
        "feedback": feedback
    }), 200

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

def extract_text_from_pdf(filepath):
    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text.strip()

def extract_score_from_feedback(feedback):
    match = re.search(r"\bScore\b.*?(\d{1,3})", feedback)
    return int(match.group(1)) if match else 0

@app.route("/", methods=["GET", "POST"])
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
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
            score = extract_score_from_feedback(feedback)
            print("Score:", score, type(score))
            return render_template("results.html", resume=resume_text, feedback=feedback, score=score)
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


@app.route("/fixit", methods=["GET", "POST"])
def fixit():
    return render_template("fixit.html")


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

    return render_template("rewrite_resume_based_on_feedback.html", rewrites=rewrites)

@app.route("/rewrite_resume_auto", methods=["POST"])
def rewrite_resume_auto():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    resume = request.form.get("resume", "")
    job_description = request.form.get("job_description", "")

    prompt = f"""You are a professional resume editor and recruiter. Rewrite this resume to:
    - Increase the match score with the job description
    - Use strong action verbs and measurable results
    - Add keywords that align with the job
    - Improve formatting, clarity, and impact

    Job Description:
    {job_description}

    Resume:
    {resume}

    Output only the rewritten resume, nothing else.
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

    return render_template("rewrite_result.html", original=resume, rewritten=rewritten_resume, score=score, feedback=feedback)

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

@app.route("/keyword_heatmap", methods=["POST"])
def keyword_heatmap():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    resume = request.form.get("resume", "")
    job_description = request.form.get("job_description", "")

    job_keywords = get_job_keywords(job_description)
    data = keyword_overlap(job_keywords, resume)

    # Sort top 20 keywords
    data = sorted(data, key=lambda x: x[1], reverse=True)[:20]
    words, counts = zip(*data)

    return render_template("keyword_heatmap.html", words=words, counts=counts)

if __name__ == "__main__":
    app.run(debug=True, host="localhost", port=5050)