
#  SmartCV — AI-Powered Résumé Analyzer

SmartCV is a Flask-based web app that helps you analyze and improve your résumé to better match job descriptions using GPT-3.5. It offers actionable AI feedback, rewriting tools, and keyword heatmaps to boost your ATS success.

---

##  Features

- ✅ Upload your PDF résumé  
- ✅ Paste a job description (optional)  
- 🧠 Get detailed AI feedback (match score, missing skills, tailored suggestions)  
- ✍️ Rewrite your résumé with AI-powered improvements  
- 📊 Visualize keyword coverage with interactive heatmaps  
- 🆚 Side-by-side comparison of original vs. rewritten résumé  
- 🔐 Login-protected dashboard  

---
Fully deployed website link: https://smartcv.onrender.com/
---
---

##  Tech Stack

- **Frontend:** HTML, Bootstrap 5, Plotly.js  
- **Backend:** Flask (Python)  
- **AI Engine:** OpenAI GPT-3.5 Turbo  
- **PDF Parsing:** pdfplumber  
- **Authentication:** Flask Sessions  

---

##  Screenshots

| Upload Resume | Match Score | Keyword Heatmap |
|---|---|---|
| ![Upload](static/screenshots/upload.png) | ![Score](static/screenshots/score.png) | ![Heatmap](static/screenshots/heatmap.png) |

---

##  Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/Enochteo/resume-analyzer.git
cd resume-analyzer
```

### 2. Create and Activate a Virtual Environment

**macOS/Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application


**If using Django (adjust accordingly):**
```bash
python manage.py runserver
```

Then visit:    
- `http://127.0.0.1:8000` (Django)

---



##  Contributing

1. Fork the repo
2. Clone your fork: `git clone https://github.com/your-username/resume-analyzer.git`
3. Create a new branch: `git checkout -b feature/your-feature`
4. Commit and push: `git commit -m "✨ Add feature"`
5. Open a Pull Request and explain what you changed. Thanks.

Check the [Issues](https://github.com/Enochteo/resume-analyzer/issues) tab for ideas!
---

##  Author

**Enoch Owoade** 

📧 [enochowoade@gmail.com] 
🌐 [https://www.linkedin.com/in/enoch-owoade/]
🌐 [https://www.github.com/Enochteo]

🌐 [https://enochsportfolio.netlify.app/]

=======
