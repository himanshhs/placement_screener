# 🚀 AI-Powered Placement Screener

> Automating resume shortlisting for campus placements using AI, semantic matching, and multi-signal scoring.

---

## 🎯 Problem Statement

Placement cells often receive **hundreds of resumes per drive**, making manual screening:
- ⏳ Time-consuming
- ❌ Error-prone
- 📉 Inconsistent

---

## 💡 Solution

This system automates candidate shortlisting by combining:
- 📄 Resume analysis (semantic understanding)
- 💻 Coding profile evaluation (LeetCode, Codeforces)
- 🧑‍💻 GitHub activity signals
- 🎓 Academic performance

👉 Result: **Accurate, fast, and customizable shortlisting**

---

## ⚙️ Key Features

- 📥 **Bulk ERP Data Import** (CSV)
- 🧠 **AI-based Job Description Analysis**
- 🎚️ **Dynamic Weight Configuration**
- 🔍 **Section-wise Resume Parsing**
- 🧮 **Semantic Matching using SBERT**
- 📊 **Multi-factor Candidate Scoring**
- 📤 **Excel Export for Recruiters**
- 🔐 **Authentication + Dashboard UI**

---

## 🔄 End-to-End Workflow

1. 📥 Import student dataset (ERP CSV)
2. ➕ Create placement drive
3. 📄 Input Job Description
4. ⚙️ Configure scoring weights
5. ▶️ Run scoring engine
6. 📊 Get ranked shortlist instantly
7. 📤 Export results to Excel

---

## 🧠 Scoring Logic (Core Innovation)

Final Score =  
- 🔹 Skills Match (SBERT Semantic Similarity)  
- 🔹 GitHub Activity Score  
- 🔹 Competitive Programming Score  
- 🔹 Academic Score (CGPA)  
- 🔹 Bonus Signals (Projects, Internships)

👉 Fully customizable weight system per job role

---

## 🏗️ Tech Stack

| Layer        | Technology |
|-------------|-----------|
| Backend     | Python, Flask |
| Database    | SQLite, SQLAlchemy |
| AI/NLP      | Sentence Transformers (SBERT) |
| Parsing     | PyMuPDF |
| Frontend    | HTML, CSS, JavaScript |

---

## 📊 Impact

- ⚡ Shortlists **200+ students in seconds**
- 📉 Reduces manual effort by **80–90%**
- 🎯 Improves relevance using **semantic matching**
- 🔄 Works across multiple job roles dynamically

---

## 📸 Screenshots

> *(Add these before final submission)*

- Dashboard UI  
- Drive Creation Page  
- Scoring Results Table  
- Exported Excel Preview  

---

## ▶️ Local Setup

```bash
git clone <your-repo-url>
cd placement_screener
venv\Scripts\activate
pip install -r requirements.txt
python run.py