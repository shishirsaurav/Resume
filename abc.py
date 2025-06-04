"""
Generate sample candidate data for testing the candidate matcher system
"""

import pandas as pd
import random
from datetime import datetime

def generate_sample_candidates():
    """Generate sample candidate data"""
    
    # Sample data pools
    names = [
        "Rahul Sharma", "Priya Singh", "Amit Kumar", "Sneha Patel", "Vikram Gupta",
        "Anita Mehta", "Rajesh Verma", "Kavya Nair", "Suresh Reddy", "Deepika Joshi",
        "Arjun Malhotra", "Meera Agarwal", "Sanjay Rao", "Pooja Bansal", "Nikhil Shah",
        "Ritu Kapoor", "Manoj Tiwari", "Swati Saxena", "Karan Chopra", "Shikha Mishra",
        "Varun Sinha", "Neha Gupta", "Rohit Pandey", "Anjali Bhatt", "Sachin Jain",
        "Shreya Kulkarni", "Vishal Singh", "Preeti Sharma", "Gaurav Kumar", "Nisha Patil"
    ]
    
    locations = [
        "delhi", "mumbai", "bangalore", "pune", "hyderabad", 
        "chennai", "kolkata", "ahmedabad", "jaipur", "noida",
        "gurgaon", "indore", "bhopal", "lucknow", "kanpur"
    ]
    
    roles = [
        "Software Engineer", "Senior Software Engineer", "Lead Developer",
        "Full Stack Developer", "Backend Developer", "Frontend Developer",
        "DevOps Engineer", "Data Scientist", "Machine Learning Engineer",
        "Product Manager", "Technical Lead", "Architect", "QA Engineer",
        "Mobile Developer", "Cloud Engineer", "Database Administrator",
        "Security Engineer", "UI/UX Designer", "Business Analyst", "Scrum Master"
    ]
    
    skills_pool = [
        # Programming Languages
        "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust", "PHP", "Ruby",
        
        # Web Technologies
        "React", "Angular", "Vue.js", "Node.js", "Express.js", "Django", "Flask", "Spring Boot",
        "HTML", "CSS", "Bootstrap", "Tailwind CSS", "jQuery", "Next.js", "Nuxt.js",
        
        # Databases
        "MySQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch", "Oracle", "SQL Server",
        "Cassandra", "DynamoDB", "Firebase", "SQLite",
        
        # Cloud Platforms
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Jenkins", "GitLab CI",
        "GitHub Actions", "CircleCI", "Ansible", "Chef", "Puppet",
        
        # Data & Analytics
        "Pandas", "NumPy", "Scikit-learn", "TensorFlow", "PyTorch", "Keras", "Apache Spark",
        "Hadoop", "Tableau", "Power BI", "R", "SAS", "SPSS",
        
        # Mobile Development
        "React Native", "Flutter", "Swift", "Kotlin", "Xamarin", "Ionic",
        
        # Others
        "Git", "Jira", "Confluence", "Slack", "Microservices", "REST API", "GraphQL",
        "Agile", "Scrum", "Unit Testing", "Integration Testing", "Linux", "Windows Server"
    ]
    
    candidates = []
    
    for i in range(200):  # Generate 200 sample candidates
        emp_id = f"EMP-{str(i+1).zfill(4)}"
        name = random.choice(names)
        location = random.choice(locations).lower()
        experience = random.randint(0, 15)
        current_role = random.choice(roles)
        
        # Generate skills based on role and experience
        num_skills = min(max(3, experience), 12)  # 3-12 skills based on experience
        candidate_skills = random.sample(skills_pool, num_skills)
        skills_str = ", ".join(candidate_skills)
        
        candidates.append({
            "Employee ID": emp_id,
            "Name": name,
            "Location": location,
            "Experience (Years)": experience,
            "Current Role": current_role,
            "Skills": skills_str
        })
    
    return candidates

def create_job_requirements_sample():
    """Create sample job requirements for testing"""
    
    job_requirements = [
        {
            "id": "JOB001",
            "job_title": "Senior Full Stack Developer",
            "rolelevel": "Senior",
            "industry": "Technology",
            "location": "bangalore",
            "role_summary": "Looking for a senior full stack developer with 5+ years experience in React, Node.js, MongoDB, and AWS. Should have experience in microservices architecture and agile development."
        },
        {
            "id": "JOB002", 
            "job_title": "Data Scientist",
            "rolelevel": "Mid",
            "industry": "Finance",
            "location": "mumbai",
            "role_summary": "Seeking a data scientist with Python, machine learning, pandas, scikit-learn experience. Should have knowledge of statistical analysis and data visualization tools like Tableau."
        },
        {
            "id": "JOB003",
            "job_title": "DevOps Engineer", 
            "rolelevel": "Senior",
            "industry": "Startup",
            "location": "pune",
            "role_summary": "Need DevOps engineer with expertise in Docker, Kubernetes, AWS, Jenkins, and Terraform. Experience with CI/CD pipelines and infrastructure as code required."
        },
        {
            "id": "JOB004",
            "job_title": "Frontend Developer",
            "rolelevel": "Junior", 
            "industry": "E-commerce",
            "location": "delhi",
            "role_summary": "Looking for frontend developer with React, JavaScript, HTML, CSS skills. Fresh graduates with good projects and internship experience are welcome."
        },
        {
            "id": "JOB005",
            "job_title": "Machine Learning Engineer",
            "rolelevel": "Senior",
            "industry": "AI/ML",
            "location": "hyderabad", 
            "role_summary": "Senior ML engineer needed with TensorFlow, PyTorch, Python expertise. Should have experience in deep learning, natural language processing, and model deployment."
        },
        {
            "id": "JOB006",
            "job_title": "Cloud Architect",
            "rolelevel": "Lead",
            "industry": "Enterprise",
            "location": "gurgaon",
            "role_summary": "Cloud architect position requiring 8+ years experience with AWS, Azure, microservices architecture, and enterprise cloud migrations. Leadership experience required."
        },
        {
            "id": "JOB007",
            "job_title": "Mobile App Developer",
            "rolelevel": "Mid",
            "industry": "Mobile",
            "location": "chennai",
            "role_summary": "Mobile developer with React Native or Flutter experience. Should have published apps on Play Store/App Store and knowledge of mobile UI/UX principles."
        },
        {
            "id": "JOB008",
            "job_title": "Backend Developer",
            "rolelevel": "Mid",
            "industry": "Fintech",
            "location": "bangalore",
            "role_summary": "Backend developer with Java, Spring Boot, microservices experience. Knowledge of database design, REST APIs, and payment gateway integrations preferred."
        }
    ]
    
    return job_requirements

def main():
    """Generate and save sample data files"""
    
    print("Generating sample candidate data...")
    
    # Generate candidate data
    candidates = generate_sample_candidates()
    df_candidates = pd.DataFrame(candidates)
    
    # Save to Excel
    with pd.ExcelWriter('candidate_profiles.xlsx', engine='openpyxl') as writer:
        df_candidates.to_excel(writer, sheet_name='Candidates', index=False)
    
    print(f"✅ Generated {len(candidates)} sample candidates in 'candidate_profiles.xlsx'")
    
    # Generate job requirements
    job_reqs = create_job_requirements_sample()
    df_jobs = pd.DataFrame(job_reqs)
    
    # Save job requirements
    with pd.ExcelWriter('sample_job_requirements.xlsx', engine='openpyxl') as writer:
        df_jobs.to_excel(writer, sheet_name='Job Requirements', index=False)
    
    print(f"✅ Generated {len(job_reqs)} sample job requirements in 'sample_job_requirements.xlsx'")
    
    # Display statistics
    print("\n📊 Candidate Statistics:")
    print(f"Total Candidates: {len(candidates)}")
    print(f"Locations: {df_candidates['Location'].nunique()}")
    print(f"Experience Range: {df_candidates['Experience (Years)'].min()}-{df_candidates['Experience (Years)'].max()} years")
    print(f"Unique Roles: {df_candidates['Current Role'].nunique()}")
    
    print("\n🏢 Location Distribution:")
    location_counts = df_candidates['Location'].value_counts().head(10)
    for location, count in location_counts.items():
        print(f"  {location}: {count}")
    
    print("\n💼 Experience Distribution:")
    exp_ranges = {
        'Junior (0-2 years)': len(df_candidates[df_candidates['Experience (Years)'] <= 2]),
        'Mid (3-5 years)': len(df_candidates[(df_candidates['Experience (Years)'] > 2) & (df_candidates['Experience (Years)'] <= 5)]),
        'Senior (6+ years)': len(df_candidates[df_candidates['Experience (Years)'] > 5])
    }
    for range_name, count in exp_ranges.items():
        print(f"  {range_name}: {count}")
    
    print("\n🎯 Sample Job Requirements Generated:")
    for job in job_reqs:
        print(f"  {job['id']}: {job['job_title']} ({job['rolelevel']}) - {job['location']}")
    
    print("\n✨ Sample data generation completed!")
    print("Upload 'candidate_profiles.xlsx' to your GCS bucket and use the API to test matching.")

if _name_ == "_main_":
    main()
