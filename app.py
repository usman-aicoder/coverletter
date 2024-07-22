import streamlit as st
from openai import OpenAI
from docx import Document
import requests
from bs4 import BeautifulSoup
import io
import os
from dotenv import load_dotenv
import re
import PyPDF2

# Load environment variables
load_dotenv()

# Set up OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
def extract_job_description(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    job_description = ""
    description_container = soup.find('div', class_=re.compile('description__text|show-more-less-html__markup'))
    
    if description_container:
        job_description = description_container.get_text(separator='\n', strip=True)
    
    if not job_description:
        description_div = soup.find('div', class_=lambda x: x and 'job-description' in x)
        if description_div:
            job_description = description_div.get_text(separator='\n', strip=True)
    
    return job_description if job_description else "Could not extract job description automatically."

def parse_job_details(job_description):
    lines = job_description.split('\n')
    
    requirements = []
    responsibilities = []
    current_section = None

    for line in lines:
        line = line.strip()
        if re.search(r'requirements|qualifications', line, re.IGNORECASE):
            current_section = 'requirements'
        elif re.search(r'responsibilities|duties', line, re.IGNORECASE):
            current_section = 'responsibilities'
        elif line and current_section:
            if current_section == 'requirements':
                requirements.append(line)
            elif current_section == 'responsibilities':
                responsibilities.append(line)

    return requirements, responsibilities

def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_cv_sections(cv_text):
    # Convert the text to lowercase for case-insensitive matching
    cv_text_lower = cv_text.lower()
    
    # Define patterns for education and experience sections
    education_patterns = [
        r'education',
        r'academic background',
        r'qualifications',
        r'degrees',
        r'academic history'
    ]
    
    experience_patterns = [
        r'experience',
        r'work history',
        r'professional background',
        r'employment',
        r'career history',
        r'internship',
        r'freelance',
        r'projects'
    ]
    
    # Function to find the start index of a section
    def find_section_start(patterns):
        indices = [cv_text_lower.find(pattern) for pattern in patterns if cv_text_lower.find(pattern) != -1]
        return min(indices) if indices else -1
    
    # Function to extract a section
    def extract_section(start_index, end_index):
        if start_index != -1 and end_index != -1:
            return cv_text[start_index:end_index].strip()
        elif start_index != -1:
            return cv_text[start_index:].strip()
        return None
    
    # Find the start indices of each section
    education_start = find_section_start(education_patterns)
    experience_start = find_section_start(experience_patterns)
    
    # Determine the end of each section (start of the next section or end of CV)
    education_end = experience_start if experience_start > education_start else -1
    experience_end = education_start if education_start > experience_start else -1
    
    # Extract the sections
    education = extract_section(education_start, education_end)
    experience = extract_section(experience_start, experience_end)
    
    return {
        "education": education,
        "experience": experience
    }

def generate_cover_letter(job_description, user_bio="", cv_sections=None):
    requirements, responsibilities = parse_job_details(job_description)

    # Use default values if user_bio or cv_sections are empty
    user_bio = user_bio or "As a professional seeking new opportunities, I am excited to apply for this position."
    cv_sections = cv_sections or {
        "contact_info": "No contact information provided",
        "experience": "No experience information provided",
        "skills": "No skills information provided"
    }

    prompt = f"""
    Job Description: {job_description}

    Requirements:
    {' '.join(f'- {req}' for req in requirements) if requirements else 'Not specified in the job description.'}

    Responsibilities:
    {' '.join(f'- {resp}' for resp in responsibilities) if responsibilities else 'Not specified in the job description.'}
    
    User Bio: {user_bio}
    
    Contact Information:
    {cv_sections['contact_info']}
    
    Relevant Experience:
    {cv_sections['experience']}
    
    Skills:
    {cv_sections['skills']}
    
    Generate a professional cover letter for the above job, tailored to the user's bio and CV information. 
    Ensure to:
    - Include a personalized greeting using the contact information provided (if available).
    - Write an engaging introduction that mentions the job title and the company.
    - Highlight specific skills and experiences from the user's CV that match the job requirements.
    - Provide specific examples or achievements from the user's past roles that demonstrate their qualifications.
    - Explain why the user is excited about this role and how they can contribute to the company's success.
    - Include a professional closing statement with a call to action.
    - Use proper formatting and a respectful tone throughout.
    - Keep the cover letter concise, ideally around 300-400 words.
    
    After the cover letter, suggest some relevant CV improvements based on the job requirements and responsibilities.
    """
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a professional cover letter writer."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return prompt, response.choices[0].message.content.strip()

def save_as_docx(text):
    doc = Document()
    doc.add_paragraph(text)
    bio = io.BytesIO()
    doc.save(bio)
    return bio
def generate_ats_score(job_description, cv_text):
    prompt = f"""
    System: You are an expert in analyzing resumes and optimizing them for Applicant Tracking Systems (ATS). When given a resume, you will provide an ATS score based on how well the resume is likely to perform when submitted to an ATS. Consider factors such as keyword usage, formatting, and overall structure. The ATS score ranges from 0 to 100, with higher scores indicating better optimization for ATS.

    User: Please analyze the following resume for ATS optimization. Here's the job description and the CV content:

    Job Description:
    {job_description}

    CV Content:
    {cv_text}

    System: Thank you for providing the resume and job description. I will now analyze them and provide an ATS score along with feedback on how to improve the resume for better ATS performance.

    Analysis:
    1. Keyword Optimization:
       * Check for relevant keywords related to the job description.
       * Evaluate the density and placement of these keywords throughout the resume.
    2. Formatting:
       * Assess the use of standard fonts, sizes, and overall readability.
       * Check for the presence of section headers such as "Experience," "Education," "Skills," etc.
       * Ensure the resume avoids complex formatting like tables, images, and columns that ATS may not read well.
    3. Structure and Content:
       * Verify that contact information is clearly listed and easily readable.
       * Evaluate the logical flow of information from top to bottom.
       * Check for any grammatical errors or typos.

    Scoring:
    Based on the analysis, provide an ATS score from 0 to 100, with a brief explanation for each aspect evaluated:
    * Keyword Optimization: (Score out of 40)
    * Formatting: (Score out of 30)
    * Structure and Content: (Score out of 30)

    Feedback:
    Provide specific feedback and suggestions on how to improve the resume in each area evaluated. For example, recommend adding more relevant keywords, simplifying formatting, or re-organizing sections for better readability.

    User: Please provide the ATS score and feedback based on the given job description and CV content.

    Assistant: Certainly! I'll analyze the CV against the job description and provide an ATS score along with detailed feedback.

    """

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an expert ATS analyzer."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content.strip()
def main():
    st.title("AI Cover Letter Generator with ATS Scoring")

    st.info("For the best results, provide as much information as possible. The job description and your CV are required for ATS scoring.")

    input_method = st.radio("Choose input method for job description:", ("Automatic (from URL)", "Manual Entry"))

    job_description = ""
    if input_method == "Automatic (from URL)":
        job_url = st.text_input("Enter the LinkedIn job posting URL:")
        if job_url:
            with st.spinner("Extracting job description..."):
                job_description = extract_job_description(job_url)
            st.subheader("Extracted Job Description:")
            st.write(job_description)
    else:
        job_description = st.text_area("Enter the job description manually:")

    user_bio = st.text_area("Enter your bio and any relevant information (optional):")

    uploaded_file = st.file_uploader("Upload your CV (PDF format)", type="pdf")
    cv_text = ""
    cv_sections = None
    if uploaded_file is not None:
        with st.spinner("Extracting text from CV..."):
            cv_text = extract_text_from_pdf(uploaded_file)
            cv_sections = extract_cv_sections(cv_text)
        
        st.subheader("Extracted CV Sections:")
        if cv_sections:
            for section, content in cv_sections.items():
                if content:
                    st.markdown(f"**{section.replace('_', ' ').title()}:**")
                    st.write(content)
                else:
                    st.warning(f"No {section.replace('_', ' ')} found in the CV.")
        else:
            st.warning("Unable to extract sections from the CV. The cover letter may be less personalized.")

    if st.button("Generate Cover Letter and ATS Score"):
        if job_description and cv_text:
            with st.spinner("Generating cover letter and ATS score..."):
                prompt, cover_letter = generate_cover_letter(job_description, user_bio, cv_sections)
                ats_score = generate_ats_score(job_description, cv_text)
            
            st.subheader("Generated Cover Letter:")
            st.write(cover_letter)
            
            docx_file = save_as_docx(cover_letter)
            st.download_button(
                label="Download Cover Letter as Word Document",
                data=docx_file.getvalue(),
                file_name="cover_letter.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

            st.subheader("ATS Score and Feedback:")
            st.write(ats_score)
        else:
            st.error("Please provide both a job description and upload your CV to generate a cover letter and ATS score.")

if __name__ == "__main__":
    main()