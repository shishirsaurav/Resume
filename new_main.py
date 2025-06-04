import os
import pandas as pd
from flask import Flask, request, jsonify
from google import genai
from google.genai import types
from google.cloud import storage
from pinecone import Pinecone
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(_name_)

app = Flask(_name_)

# === CONFIG: Environment Variables ===
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
VECTOR_HOST = os.getenv("VECTOR_HOST")
SPARSE_HOST = os.getenv("SPARSE_HOST")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GCP_BUCKET_NAME = os.getenv("GCP_BUCKET_NAME")
EXCEL_FILE_PATH = os.getenv("EXCEL_FILE_PATH", "candidate_profiles.xlsx")
VECTOR_NAMESPACE = "resume-experience"
SPARSE_NAMESPACE = "resume-skills"

# Initialize clients
try:
    pc = Pinecone(api_key=PINECONE_API_KEY)
    vector_index = pc.Index(host=VECTOR_HOST)
    sparse_index = pc.Index(host=SPARSE_HOST)
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    storage_client = storage.Client()
    logger.info("All clients initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize clients: {str(e)}")
    raise

def download_excel_from_gcs():
    """Download Excel file from GCS bucket"""
    try:
        bucket = storage_client.bucket(GCP_BUCKET_NAME)
        blob = bucket.blob(EXCEL_FILE_PATH)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            blob.download_to_filename(temp_file.name)
            logger.info(f"Downloaded {EXCEL_FILE_PATH} from GCS")
            return temp_file.name
    except Exception as e:
        logger.error(f"Error downloading file from GCS: {str(e)}")
        raise

def build_filter(location, level):
    """Build filter for Pinecone search based on location and experience level"""
    f = {"location": {"$eq": location.lower()}}
    lvl = level.strip().lower()
    
    if lvl in ["junior", "entry"]:
        f["experience"] = {"$lte": 2}
    elif lvl in ["mid", "middle", "intermediate"]:
        f["experience"] = {"$gt": 2, "$lt": 5}
    elif lvl in ["senior", "sr"]:
        f["experience"] = {"$gte": 5}
    else:
        # Default to no experience filter if level is unclear
        pass
    
    return f

def extract_skills_with_gemini(job_description):
    """Extract skills from job description using Gemini"""
    try:
        prompt = (
            "You are a recruiting assistant. Extract the essential technical skills, "
            "technologies, programming languages, frameworks, and tools from the following "
            "job description. Return them as a comma-separated list without any additional text."
        )
        
        gem_resp = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(system_instruction=prompt),
            contents=job_description,
        )
        
        skills_csv = gem_resp.text.strip()
        logger.info(f"Extracted skills: {skills_csv}")
        return skills_csv
    except Exception as e:
        logger.error(f"Error extracting skills with Gemini: {str(e)}")
        return ""

def run_candidate_search(job_description, metadata_filter, top_k=50):
    """Run hybrid search (vector + sparse) for candidates"""
    try:
        # 1) Extract skills via Gemini
        skills_csv = extract_skills_with_gemini(job_description)
        
        # 2) Vector search for experience matching
        vec_res = vector_index.search(
            namespace=VECTOR_NAMESPACE,
            query={
                "inputs": {"text": job_description}, 
                "top_k": top_k, 
                "filter": metadata_filter
            },
            fields=["current_role", "location", "experience", "text"]
        )
        hits_v = vec_res.get("result", {}).get("hits", [])
        
        # 3) Sparse search for skills matching
        sp_res = sparse_index.search(
            namespace=SPARSE_NAMESPACE,
            query={
                "inputs": {"text": skills_csv}, 
                "top_k": top_k, 
                "filter": metadata_filter
            },
            fields=["current_role", "location", "experience", "text"]
        )
        hits_s = sp_res.get("result", {}).get("hits", [])
        
        # 4) Build DataFrames
        df_v = pd.DataFrame([
            {
                "id": h["_id"], 
                "vec_score": h["_score"], 
                **h.get("fields", {})
            } for h in hits_v
        ])
        
        df_s = pd.DataFrame([
            {
                "id": h["_id"], 
                "sp_score": h["_score"], 
                **h.get("fields", {})
            } for h in hits_s
        ])
        
        # 5) Merge and sort results
        if df_v.empty and df_s.empty:
            return pd.DataFrame(), skills_csv
        elif df_v.empty:
            return df_s, skills_csv
        elif df_s.empty:
            return df_v, skills_csv
        else:
            # Inner join on common candidates
            df_merged = pd.merge(
                df_v, df_s, 
                on=["id", "location", "experience"], 
                how="inner"
            )
            
            # Calculate combined score
            df_merged["combined_score"] = (
                df_merged["vec_score"] * 0.6 + df_merged["sp_score"] * 0.4
            )
            
            df_merged = df_merged.sort_values(
                by="combined_score", 
                ascending=False
            )
            
            return df_merged, skills_csv
            
    except Exception as e:
        logger.error(f"Error in candidate search: {str(e)}")
        return pd.DataFrame(), ""

def get_candidate_details_from_excel(candidate_ids, excel_path):
    """Get detailed candidate information from Excel file"""
    try:
        df_candidates = pd.read_excel(excel_path)
        
        # Filter candidates by IDs
        matched_candidates = df_candidates[
            df_candidates['Employee ID'].astype(str).isin(candidate_ids)
        ]
        
        return matched_candidates.to_dict('records')
    except Exception as e:
        logger.error(f"Error reading candidate details: {str(e)}")
        return []

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "candidate-matcher"}), 200

@app.route('/candidates/search', methods=['POST'])
def search_candidates():
    """POST API to search for matching candidates"""
    try:
        # Validate request
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        
        # Required fields
        required_fields = ['id', 'job_title', 'rolelevel', 'location', 'role_summary']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {missing_fields}"
            }), 400
        
        # Extract request data
        req_id = data['id']
        job_title = data['job_title']
        role_level = data['rolelevel']
        location = data['location']
        role_summary = data['role_summary']
        industry = data.get('industry', '')
        
        # Build search filter
        search_filter = build_filter(location, role_level)
        
        # Run candidate search
        df_results, extracted_skills = run_candidate_search(
            job_description=role_summary,
            metadata_filter=search_filter,
            top_k=50
        )
        
        if df_results.empty:
            return jsonify({
                "request_id": req_id,
                "job_title": job_title,
                "matches_found": 0,
                "candidates": [],
                "extracted_skills": extracted_skills,
                "message": "No matching candidates found"
            }), 200
        
        # Download Excel file from GCS
        excel_path = download_excel_from_gcs()
        
        # Get detailed candidate info
        candidate_ids = df_results['id'].tolist()
        candidate_details = get_candidate_details_from_excel(candidate_ids, excel_path)
        
        # Combine search results with candidate details
        candidates = []
        for _, row in df_results.iterrows():
            candidate_detail = next(
                (c for c in candidate_details if str(c.get('Employee ID')) == str(row['id'])), 
                {}
            )
            
            candidate = {
                "candidate_id": row['id'],
                "name": candidate_detail.get('Name', 'N/A'),
                "current_role": row.get('current_role', 'N/A'),
                "location": row.get('location', 'N/A'),
                "experience_years": row.get('experience', 0),
                "skills": candidate_detail.get('Skills', 'N/A'),
                "vector_score": round(row.get('vec_score', 0), 3),
                "sparse_score": round(row.get('sp_score', 0), 3),
                "combined_score": round(row.get('combined_score', 0), 3)
            }
            candidates.append(candidate)
        
        # Clean up temporary file
        try:
            os.unlink(excel_path)
        except:
            pass
        
        return jsonify({
            "request_id": req_id,
            "job_title": job_title,
            "role_level": role_level,
            "location": location,
            "industry": industry,
            "matches_found": len(candidates),
            "candidates": candidates[:20],  # Limit to top 20 matches
            "extracted_skills": extracted_skills,
            "search_metadata": {
                "total_vector_hits": len(df_results),
                "filter_applied": search_filter
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in search_candidates: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

@app.route('/candidates/bulk', methods=['POST'])
def bulk_search_candidates():
    """POST API for bulk candidate search"""
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        job_requirements = data.get('job_requirements', [])
        
        if not job_requirements:
            return jsonify({"error": "job_requirements array is required"}), 400
        
        results = []
        
        # Download Excel file once for all searches
        excel_path = download_excel_from_gcs()
        
        # Process each job requirement
        with ThreadPoolExecutor(max_workers=min(5, len(job_requirements))) as executor:
            futures = {}
            
            for job_req in job_requirements:
                # Validate each job requirement
                required_fields = ['id', 'job_title', 'rolelevel', 'location', 'role_summary']
                if all(field in job_req for field in required_fields):
                    search_filter = build_filter(job_req['location'], job_req['rolelevel'])
                    future = executor.submit(
                        run_candidate_search,
                        job_req['role_summary'],
                        search_filter,
                        30
                    )
                    futures[future] = job_req
            
            # Collect results
            for future in as_completed(futures):
                job_req = futures[future]
                try:
                    df_results, extracted_skills = future.result()
                    
                    candidates = []
                    if not df_results.empty:
                        candidate_ids = df_results['id'].tolist()
                        candidate_details = get_candidate_details_from_excel(candidate_ids, excel_path)
                        
                        for _, row in df_results.iterrows():
                            candidate_detail = next(
                                (c for c in candidate_details if str(c.get('Employee ID')) == str(row['id'])), 
                                {}
                            )
                            
                            candidate = {
                                "candidate_id": row['id'],
                                "name": candidate_detail.get('Name', 'N/A'),
                                "current_role": row.get('current_role', 'N/A'),
                                "combined_score": round(row.get('combined_score', 0), 3)
                            }
                            candidates.append(candidate)
                    
                    results.append({
                        "request_id": job_req['id'],
                        "job_title": job_req['job_title'],
                        "matches_found": len(candidates),
                        "top_candidates": candidates[:10],  # Top 10 for bulk
                        "extracted_skills": extracted_skills
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing job {job_req['id']}: {str(e)}")
                    results.append({
                        "request_id": job_req['id'],
                        "job_title": job_req.get('job_title', 'N/A'),
                        "error": str(e)
                    })
        
        # Clean up temporary file
        try:
            os.unlink(excel_path)
        except:
            pass
        
        return jsonify({
            "total_jobs_processed": len(results),
            "results": results
        }), 200
        
    except Exception as e:
        logger.error(f"Error in bulk_search_candidates: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

@app.route('/candidates/stats', methods=['GET'])
def get_candidate_stats():
    """GET API to retrieve candidate database statistics"""
    try:
        # Download Excel file from GCS
        excel_path = download_excel_from_gcs()
        df_candidates = pd.read_excel(excel_path)
        
        # Calculate statistics
        total_candidates = len(df_candidates)
        location_stats = df_candidates['Location'].value_counts().to_dict()
        experience_stats = df_candidates.groupby('Experience (Years)').size().to_dict()
        role_stats = df_candidates['Current Role'].value_counts().head(10).to_dict()
        
        # Clean up temporary file
        try:
            os.unlink(excel_path)
        except:
            pass
        
        return jsonify({
            "total_candidates": total_candidates,
            "location_distribution": location_stats,
            "experience_distribution": experience_stats,
            "top_roles": role_stats,
            "last_updated": "Retrieved from GCS"
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_candidate_stats: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

if _name_ == '_main_':
    app.run(debug=True, host='0.0.0.0', port=8080)
