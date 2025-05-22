# app.py
# pip install streamlit pinecone pandas PyPDF2 openpyxl

import os
import re
import time
import zipfile
import tempfile

import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
from pinecone import Pinecone

# === CONFIGURE YOUR KEYS/HOSTS ===
PINECONE_API_KEY   = os.getenv("PINECONE_API_KEY")
VECTOR_HOST        = os.getenv("PINECONE_VECTOR_HOST")
SPARSE_HOST        = os.getenv("PINECONE_SPARSE_HOST")
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY")
NAMESPACE_VECTOR   = "resume-experience"
NAMESPACE_SPARSE   = "resume-skills"



# =================================

# Initialize Pinecone
pc            = Pinecone(api_key=PINECONE_API_KEY)
vector_index  = pc.Index(host=VECTOR_HOST)
sparse_index  = pc.Index(host=SPARSE_HOST)

def extract_project_experience(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    m = re.search(r'Project Experience:(.*)', text, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""

def upsert_candidate(emp_id, name, loc, exp, role, skills, resume_folder):
    # metadata
    meta = {
        "location":     loc,
        "experience":   exp,
        "current_role": role
    }

    # 1) Vector upsert: project experience
    fname = f"{emp_id}_{name.replace(' ', '_')}.pdf"
    pdf_path = os.path.join(resume_folder, fname)
    try:
        proj_text = extract_project_experience(pdf_path)
        if proj_text:
            vector_index.upsert_records(
                NAMESPACE_VECTOR,
                [{ "_id": emp_id, "text": proj_text, **meta }]
            )
        else:
            st.warning(f"No ‘Project Experience’ found in {fname}")
    except FileNotFoundError:
        st.error(f"Missing resume file: {fname}")

    # 2) Sparse upsert: skills
    sparse_index.upsert_records(
        NAMESPACE_SPARSE,
        [{ "_id": emp_id, "text": skills, **meta }]
    )

st.title("Upload associate profiles")

st.markdown("""
Upload:
- A `.zip` containing all resumes named like `EMP-XXXX_Name.pdf`  
- An Excel (`.xlsx`) with columns exactly:
  `Employee ID, Name, Location, Experience (Years), Current Role, Skills`
""")

zip_uploader   = st.file_uploader("🔀 Upload resumes ZIP", type="zip")
excel_uploader = st.file_uploader("📊 Upload candidates Excel", type=["xlsx","xls"])

if st.button("▶️ Process and Upsert") and zip_uploader and excel_uploader:
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1) Extract ZIP
        with zipfile.ZipFile(zip_uploader) as zf:
            zf.extractall(tmpdir)
        st.success("✅ Resumes extracted")

        # 2) Load Excel
        df = pd.read_excel(excel_uploader, engine="openpyxl")
        total = len(df)
        st.write(f"Found {total} candidates in Excel")

        # 3) Progress bar
        prog = st.progress(0)

        # 4) Iterate and upsert
        for idx, row in df.iterrows():
            upsert_candidate(
                emp_id        = str(row["Employee ID"]),
                name          = row["Name"],
                loc           = row["Location"],
                exp           = row["Experience (Years)"],
                role          = row["Current Role"],
                skills        = row["Skills"],
                resume_folder = tmpdir
            )
            # update progress
            percent = int((idx + 1) / total * 100)
            prog.progress(percent)
            time.sleep(0.2)  # throttle

        # 5) Wait for indexing
        st.info("Waiting for Pinecone to finish indexing…")
        time.sleep(5)
        st.success("🎉 All records upserted!")
else:
    st.info("Awaiting both ZIP and Excel uploads…")
