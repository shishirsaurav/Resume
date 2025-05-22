import streamlit as st

# ————— STREAMLIT CONFIG —————
st.set_page_config(
    page_title="Candidate Portal Home", 
    page_icon="🏠", 
    layout="wide",
)

# ————— SIDEBAR NAVIGATION —————
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "", ["Home"]
)

# ————— PAGES —————
if page == "Home":
    st.title("🏠 Candidate Portal Dashboard")
    st.markdown(
        """
        **Welcome to the Candidate Portal!**

        This platform leverages Streamlit, OpenAI, and Pinecone to provide:

        - **Resume Parsing** via GPT-4o: Extract structured fields (experience, projects, skills, education).
        - **Multi-Namespace Indexing**: Separate Pinecone namespaces for experience, projects, education, and skills.
        - **Semantic & Sparse Search**: Combine dense embeddings and sparse vector search for skills matching.
        - **Weighted Scoring & Reranking**: Customizable weight sliders for each facet with Pinecone’s `rerank` feature.
        - **Metadata Filtering**: Filter candidates by interests (e.g. Machine Learning, UI/UX).
        - **Cutoff Thresholding**: Set minimum overall score to surface best-fit candidates.

        ## Architecture Overview
        1. **Upload Pipeline**
           - User uploads PDF resume
           - Text extracted via `PyPDF`
           - LLM extracts JSON fields
           - Data upserted to four Pinecone namespaces

        2. **Search Pipeline**
           - Hiring manager uploads a Job Description
           - LLM parses requirements into four paragraphs
           - Four separate searches (experience, projects, education, skills)
           - Metadata filters applied
           - Scores aggregated, weighted, reranked, and filtered by cutoff

        ## Getting Started
        - Use the **Upload Resume** page to add candidates.
        - Use the **Search Candidates** page to find top matches based on JD requirements.

        _Developed by Shishir Saurav._
        """
    )
    st.image("shishir.jpg","architecture diagram")

elif page == "Upload Resume":
    # Delegate to upload_resume_pinecone.py
    st.experimental_set_query_params(page="upload")
    st.write("Navigate to the Upload Resume page in the sidebar.")

else:
    # Delegate to search_candidates_pinecone.py
    st.experimental_set_query_params(page="search")
    st.write("Navigate to the Search Candidates page in the sidebar.")

# Optional: Footer
st.markdown("---")
st.markdown(
    "<center>© 2025 Candidate Portal · Shishir Saurav</center>",
    unsafe_allow_html=True
)
