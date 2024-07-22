import streamlit as st
from openai import OpenAI
from docx import Document
import requests
from bs4 import BeautifulSoup
import io
import os
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()
# Get the API key
api_key = os.getenv("OPENAI_API_KEY")
# Set up OpenAI client
if api_key:
    obscured_key = f"sk-...{api_key[-4:]}"
    st.sidebar.write(f"API Key loaded: {obscured_key}")
else:
    st.sidebar.error("API Key not found in environment variables")

# Set up OpenAI client
client = OpenAI(api_key=api_key)
#client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_job_description(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Try to extract job description from LinkedIn
    job_description = ""
    
    # Look for the job description container
    description_container = soup.find('div', class_=re.compile('description__text|show-more-less-html__markup'))
    
    if description_container:
        # Extract all text from the container
        job_description = description_container.get_text(separator='\n', strip=True)
    
    # If we couldn't find the job description, try a more general approach
    if not job_description:
        # Look for any div with 'job-description' in its class
        description_div = soup.find('div', class_=lambda x: x and 'job-description' in x)
        if description_div:
            job_description = description_div.get_text(separator='\n', strip=True)
    
    return job_description if job_description else "Could not extract job description automatically."

def parse_job_details(job_description):
    # Split the job description into lines
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

def generate_cover_letter(job_description, user_bio):
    requirements, responsibilities = parse_job_details(job_description)

    prompt = f"""
    Job Description: {job_description}

    Requirements:
    {' '.join(f'- {req}' for req in requirements) if requirements else 'Not specified in the job description.'}

    Responsibilities:
    {' '.join(f'- {resp}' for resp in responsibilities) if responsibilities else 'Not specified in the job description.'}
    
    User Bio: {user_bio}
    
    Generate a professional cover letter for the above job, tailored to the user's bio. The cover letter should include
    Ensure to address the specific requirements and responsibilities if provided.
    - A personalized greeting.
    - An engaging introduction that mentions the job title and the company.
    - A brief summary of the user's relevant experience and skills that match the job requirements.
    - Specific examples or achievements from the user's past roles that demonstrate their qualifications.
    - An explanation of why the user is excited about this role and how they can contribute to the company's success.
    - A professional closing statement with a call to action.
    - Proper formatting and a respectful tone throughout.
    -Word limit 200
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

def main():
    st.title("AI Cover Letter Generator")

    input_method = st.radio("Choose input method:", ("Automatic (from URL)", "Manual Entry"))

    if input_method == "Automatic (from URL)":
        job_url = st.text_input("Enter the LinkedIn job posting URL:")
        if job_url:
            with st.spinner("Extracting job description..."):
                job_description = extract_job_description(job_url)
            st.subheader("Extracted Job Description:")
            st.write(job_description)
    else:
        job_description = st.text_area("Enter the job description manually:")

    user_bio = st.text_area("Enter your bio and any relevant information:")

    if st.button("Generate Cover Letter"):
        if job_description and user_bio:
            with st.spinner("Generating cover letter..."):
                prompt, cover_letter = generate_cover_letter(job_description, user_bio)
            
            st.subheader("AI Prompt:")
            st.text(prompt)
            
            st.subheader("Generated Cover Letter:")
            st.write(cover_letter)
            
            docx_file = save_as_docx(cover_letter)
            st.download_button(
                label="Download as Word Document",
                data=docx_file.getvalue(),
                file_name="cover_letter.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        else:
            st.error("Please provide both the job description and your bio.")

if __name__ == "__main__":
    main()