import os
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types
from pinecone import Pinecone
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# === CONFIG: use env vars ===
PINECONE_API_KEY   = os.getenv("PINECONE_API_KEY")
VECTOR_HOST        = os.getenv("PINECONE_VECTOR_HOST")
SPARSE_HOST        = os.getenv("PINECONE_SPARSE_HOST")
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY")
VECTOR_NAMESPACE   = "resume-experience"
SPARSE_NAMESPACE   = "resume-skills"
# ============================

# Initialize clients
pc            = Pinecone(api_key=PINECONE_API_KEY)
vector_index  = pc.Index(host=VECTOR_HOST)
sparse_index  = pc.Index(host=SPARSE_HOST)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

def build_filter(location, level):
    f = {"location": {"$eq": location}}
    lvl = level.strip().lower()
    if lvl == "junior":
        f["experience"] = {"$lte": 1}
    elif lvl == "mid":
        f["experience"] = {"$gt": 1, "$lt": 3}
    else:
        f["experience"] = {"$gt": 3}
    return f

def run_search(jd_text, md_filter, top_k=50):
    # 1) Extract skills via Gemini
    prompt = (
        "You are a recruiting assistant. Extract the essential skills from the following "
        "job description as a comma-separated list."
    )
    gem_resp = gemini_client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(system_instruction=prompt),
        contents=jd_text,
    )
    skills_csv = gem_resp.text.strip()

    # 2) Vector search
    vec_res = vector_index.search(
        namespace=VECTOR_NAMESPACE,
        query={"inputs": {"text": jd_text}, "top_k": top_k, "filter": md_filter},
        fields=["current_role","location","experience","text"]
    )
    hits_v = vec_res["result"]["hits"]

    # 3) Sparse search
    sp_res = sparse_index.search(
        namespace=SPARSE_NAMESPACE,
        query={"inputs": {"text": skills_csv}, "top_k": top_k, "filter": md_filter},
        fields=["current_role","location","experience","text"]
    )
    hits_s = sp_res["result"]["hits"]

    # 4) Build DataFrames
    df_v = pd.DataFrame([{"id": h["_id"], "vec_score": h["_score"], **h.get("fields", {})} for h in hits_v])
    df_s = pd.DataFrame([{"id": h["_id"], "sp_score": h["_score"], **h.get("fields", {})} for h in hits_s])

    # 5) Intersect & sort
    if df_v.empty or df_s.empty:
        return pd.DataFrame(), skills_csv
    df_m = pd.merge(df_v, df_s, on=["id","location","experience"], how="inner")
    df_m = df_m.sort_values(by=["vec_score","sp_score"], ascending=False)
    return df_m, skills_csv

# --- Streamlit UI ---
st.set_page_config(page_title="Bulk Candidate Matcher", layout="wide")
st.title("🤖 Candidate Matcher: Bulk by Uploaded CSV")

st.markdown("""
Upload a CSV/Excel with columns:
`Requirement ID, Job Title, Role Level, Industry, Work Location, Summary`
""")
uploaded = st.file_uploader("Upload job.xlsx", type=["xlsx","xls"])
if uploaded:
    df_jobs = pd.read_excel(uploaded)
    st.success(f"Loaded {len(df_jobs)} requirements.")

    if st.button("Find Candidates for All Jobs"):
        with st.spinner("Running searches in parallel…"):
            futures = {}
            with ThreadPoolExecutor(max_workers=min(10, len(df_jobs))) as exe:
                for _, job in df_jobs.iterrows():
                    req_id = job["Requirement ID"]
                    filt   = build_filter(location=job["Work Location"], level=job["Role Level"])
                    futures[exe.submit(run_search, job["Summary"], filt, 50)] = req_id

            for fut in as_completed(futures):
                req_id  = futures[fut]
                df_res, skills = fut.result()

                st.subheader(f"Results for {req_id}")
                if df_res.empty:
                    st.warning(f"No matches for {req_id}.")
                else:
                    st.dataframe(df_res.reset_index(drop=True))
                    st.markdown(f"**Extracted skills:** {skills}")
