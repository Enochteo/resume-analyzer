import os
import openai
from flask import Flask, render_template, request, redirect
import pdfplumber
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from openai import OpenAI

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_text_from_pdf(filepath):
    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text.strip()


@app.route("/", methods=["GET", "POST"])
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
            return render_template("results.html", resume=resume_text, feedback=feedback)
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

if __name__ == "__main__":
    app.run(debug=True)