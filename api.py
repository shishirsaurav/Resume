# main.py
# FastAPI backend for AI-Powered RMG Platform
# -------------------------------------------
# ➜  uvicorn main:app --reload   (or use any ASGI server)

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google import genai
from google.genai import types
from pinecone import Pinecone

# ------------------------------------------------------------------
# 1.  CONFIGURATION & CLIENT INITIALISATION
# ------------------------------------------------------------------
load_dotenv()                                                           # .env → environment

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
VECTOR_HOST      = os.getenv("PINECONE_VECTOR_HOST")
SPARSE_HOST      = os.getenv("PINECONE_SPARSE_HOST")
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY")

VECTOR_NAMESPACE = "resume-experience"
SPARSE_NAMESPACE = "resume-skills"

pc             = Pinecone(api_key=PINECONE_API_KEY)
vector_index   = pc.Index(host=VECTOR_HOST)
sparse_index   = pc.Index(host=SPARSE_HOST)
gemini_client  = genai.Client(api_key=GEMINI_API_KEY)

# ------------------------------------------------------------------
# 2.  HELPERS (same logic you already had)
# ------------------------------------------------------------------
def build_filter(location: str, level: str):
    f = {"location": {"$eq": location}}
    lvl = level.strip().lower()
    if lvl == "junior":
        f["experience"] = {"$lte": 1}
    elif lvl == "mid":
        f["experience"] = {"$gt": 1, "$lt": 3}
    else:
        f["experience"] = {"$gt": 3}
    return f


def run_search(jd_text: str, md_filter: dict, top_k: int = 50):
    # 1) Extract skills with Gemini-Flash
    prompt = ("You are a recruiting assistant. Extract the essential skills from the "
              "following job description as a comma-separated list.")
    gem_resp = gemini_client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(system_instruction=prompt),
        contents=jd_text,
    )
    skills_csv = gem_resp.text.strip()

    # 2) Dense / sparse searches
    vec_res = vector_index.search(
        namespace=VECTOR_NAMESPACE,
        query={"inputs": {"text": jd_text}, "top_k": top_k, "filter": md_filter},
        fields=["current_role", "location", "experience", "text"],
    )
    sp_res = sparse_index.search(
        namespace=SPARSE_NAMESPACE,
        query={"inputs": {"text": skills_csv}, "top_k": top_k, "filter": md_filter},
        fields=["current_role", "location", "experience", "text"],
    )

    # 3) Convert to DataFrames
    df_v = pd.DataFrame([{"id": h["_id"], "vec_score": h["_score"], **h.get("fields", {})}
                         for h in vec_res["result"]["hits"]])
    df_s = pd.DataFrame([{"id": h["_id"], "sp_score": h["_score"], **h.get("fields", {})}
                         for h in sp_res["result"]["hits"]])

    # 4) Intersect & sort
    if df_v.empty or df_s.empty:
        return [], skills_csv
    df_m = (df_v
            .merge(df_s, on=["id", "location", "experience"])
            .sort_values(["vec_score", "sp_score"], ascending=False))

    # 5) Return as plain dict list (easy to serialise)
    return df_m.to_dict(orient="records"), skills_csv


# ------------------------------------------------------------------
# 3.  FASTAPI DEFINITIONS
# ------------------------------------------------------------------
app = FastAPI(
    title="AI-Powered RMG Candidate Matcher",
    version="1.0.0",
    description="Backend API for the React dashboard.",
)

# Enable CORS for your local/dev front-end origin(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],  # tighten in prod!
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ----------  Pydantic models ----------
class JDRequest(BaseModel):
    requirementId: str
    jobTitle: Optional[str] = None
    roleLevel: str = "senior"
    industry: Optional[str] = None
    workLocation: str
    roleSummary: str


class MatchResponse(BaseModel):
    requirementId: str
    extractedSkills: str
    candidates: List[dict]   # (id, vec_score, sp_score, current_role, location, experience, text)


class BulkMatchResponse(BaseModel):
    results: List[MatchResponse]


# ----------  Health check ----------
@app.get("/ping")
def ping():
    return {"status": "ok"}


# ----------  Single JD endpoint ----------
@app.post("/match", response_model=MatchResponse)
def match_jd(jd: JDRequest):
    """
    Analyses a single JD and returns a ranked candidate list.
    """
    md_filter = build_filter(location=jd.workLocation, level=jd.roleLevel)
    hits, skills = run_search(jd.roleSummary, md_filter)
    return MatchResponse(requirementId=jd.requirementId,
                         extractedSkills=skills,
                         candidates=hits)


# ----------  Bulk Excel/CSV upload ----------
@app.post("/match_bulk", response_model=BulkMatchResponse)
async def match_bulk(file: UploadFile = File(...), top_k: int = 50):
    """
    Accepts an Excel/CSV file whose columns match:
    Requirement ID | Job Title | Role Level | Industry | Work Location | Summary
    Returns candidate lists for every row (runs searches in parallel).
    """
    try:
        if file.filename.endswith((".xlsx", ".xls")):
            df_jobs = pd.read_excel(file.file)
        elif file.filename.endswith(".csv"):
            df_jobs = pd.read_csv(file.file)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File read error: {e}")

    required_cols = {"Requirement ID", "Role Level", "Work Location", "Summary"}
    if not required_cols.issubset(df_jobs.columns):
        raise HTTPException(status_code=400,
                            detail=f"Input file must contain columns: {', '.join(required_cols)}")

    results: List[MatchResponse] = []
    with ThreadPoolExecutor(max_workers=min(10, len(df_jobs))) as exe:
        futures = {}
        for _, job in df_jobs.iterrows():
            filt = build_filter(location=job["Work Location"], level=job["Role Level"])
            futures[exe.submit(run_search, job["Summary"], filt, top_k)] = job["Requirement ID"]

        for fut in as_completed(futures):
            req_id = futures[fut]
            try:
                hits, skills = fut.result()
                results.append(MatchResponse(
                    requirementId=req_id, extractedSkills=skills, candidates=hits))
            except Exception as exc:
                results.append(MatchResponse(
                    requirementId=req_id, extractedSkills="",
                    candidates=[],  # empty on failure
                ))
                print(f"Search failed for {req_id}: {exc}")

    return BulkMatchResponse(results=results)
