# 🧠 Personal Mock Test Generator (AI-Powered with Gemini)

Welcome to the **Personal Mock Test Generator** – a powerful full-stack web application that uses **Google Gemini AI** to generate bilingual (English + Hindi) mock tests for competitive exams. Whether you're a student, teacher, or institution, this platform helps you **generate**, **take**, **review**, and **store** mock tests with ease!

---

## 🌟 Features

- 🤖 **AI-based Test Generation** using Gemini 2.0 Flash
- 📝 Auto-generated questions based on exam name or custom input
- 🧠 Bilingual question format (English + Hindi)
- ✍️ Three Test Creation Modes:
  - AI Generation from Exam Name
  - Text Import + AI Parsing
  - Manual Question Builder
- 📊 Auto scoring and review with explanations
- 💾 Save, list, and delete your tests
- 🎨 Beautiful, responsive UI built with TailwindCSS

---

## 🛠 Tech Stack

| Layer       | Technology                  |
|-------------|-----------------------------|
| Frontend    | HTML, TailwindCSS, JavaScript |
| Backend     | Python, FastAPI             |
| AI Engine   | Google Gemini 2.0 Flash API |
| Storage     | JSON file (`tests.json`)    |

---


## 🚀 Setup Instructions

### ✅ 1. Clone the Repository

```bash
git clone https://github.com/jitendra-2004/jitendra-2004-Personal-Mock-Test-Generator.git
cd jitendra-2004-Personal-Mock-Test-Generator


 Install Python Dependencies
pip install fastapi uvicorn python-multipart requests

Set Your Google Gemini API Key
Open main.py and replace the placeholder with your key:
API_KEY = "YOUR_GEMINI_API_KEY_HERE"


Run the Application
bash
uvicorn main:app --reload
Then open your browser:
http://127.0.0.1:8000/


📁 Project Structure
📦 project-root/
├── main.py              # FastAPI backend with Gemini API
├── tests.json           # JSON file to save test data
└── static/
    └── index.html       # Tailwind + JS powered frontend
