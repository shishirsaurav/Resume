# 📄 Resume Upserter & Bulk Candidate Matcher

Three Streamlit apps:

1. **Landing Page** (`app.py` in root) for welcome/overview.
2. **Upload Batch** (`pages/upload_batch.py`) to upsert resumes into Pinecone.
3. **Search Candidates** (`pages/Search_candidates.py`) to match jobs to candidates via Pinecone & Gemini.

---

## 📁 Repository Layout

```
.
├── .gitignore
├── .env.example      ← sample env (copy to `.env`)
├── requirements.txt
├── README.md
├── app.py            ← Landing page (root)
└── pages
    ├── upload_batch.py         ← Resume → Pinecone Upserter
    └── Search_candidates.py    ← Bulk Candidate Matcher
```

---

## ⚙️ Setup

### 1. Prerequisites

* **Python 3.8+**
* Pinecone account with:

  * API key
  * Vector index host URL
  * Sparse index host URL
* Google Cloud account with access to Generative AI (Gemini):

  * API key

### 2. Clone & venv

```bash
git clone <your-repo-url>
cd <repo-dir>
python -m venv venv
source venv/bin/activate      # macOS/Linux
venv\Scripts\activate         # Windows
```

### 3. Install deps

```bash
pip install -r requirements.txt
```

### 4. Configure

Copy and rename `.env.example` to `.env`, then fill in:

```bash
cp .env.example .env
```

```dotenv
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_VECTOR_HOST=https://your-vector-host
PINECONE_SPARSE_HOST=https://your-sparse-host
GEMINI_API_KEY=your_gemini_api_key
```

---

## 🚀 Running the Apps

### 1. Landing Page

```bash
streamlit run app.py
```

*This displays the welcome/overview screen.*

### 2. Upload Batch (Resume Upserter)

```bash
streamlit run pages/upload_batch.py
```

**Workflow:**

1. Upload a ZIP of resumes named `EMP-XXXX_Name.pdf`.
2. Upload an Excel (`.xlsx`/`.xls`) with columns:

   * `Employee ID`
   * `Name`
   * `Location`
   * `Experience (Years)`
   * `Current Role`
   * `Skills`
3. Click **Process and Upsert**.

### 3. Search Candidates (Bulk Matcher)

```bash
streamlit run pages/Search_candidates.py
```

**Workflow:**

1. Upload a CSV/Excel with columns:

   * `Requirement ID`
   * `Job Title`
   * `Role Level`
   * `Industry`
   * `Work Location`
   * `Summary`
2. Click **Find Candidates for All Jobs**.
3. View matching candidates & extracted skills for each requirement.

---

## 📝 Notes

* Ensure Pinecone indices `resume-experience` and `resume-skills` exist.
* Keep real `.env` out of version control (`.gitignore`).
* Adjust thread pool size or `top_k` in `Search_candidates.py` as needed.

---

## 📜 License

MIT
