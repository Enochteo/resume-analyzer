import os
from flask import Flask, render_template, request, redirect
import pdfplumber
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
            return render_template("results.html", resume=resume_text)
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)