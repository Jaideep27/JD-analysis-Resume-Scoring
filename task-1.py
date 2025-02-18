from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
import pdfplumber
import docx
import google.generativeai as genai
from typing import List, Optional
import os
from pydantic import BaseModel
from enum import Enum
from dotenv import load_dotenv

# Define available criteria types for dropdown
class CriteriaType(str, Enum):
    overall = "overall"
    skills = "skills"
    experience = "experience"
    certifications = "certifications"
    qualifications = "qualifications"
    education = "education"
    tools = "tools"
    languages = "languages"
    responsibilities = "responsibilities"
    benefits = "benefits"
    culture = "company culture"

# Initialize FastAPI app with detailed documentation
app = FastAPI(
    title="Job Description Analysis API",
    description="""
    This API extracts key criteria from job description documents.
    Upload a job description file and get structured information about required skills,
    experience, certifications, and other specified criteria.
    
    Select "overall" to get a comprehensive analysis of all important aspects.
    """,
    version="1.0.0"
)

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")
genai.configure(api_key=GEMINI_API_KEY)

# Define response model for better Swagger documentation
class CriteriaResponse(BaseModel):
    criteria: List[str]
    criteria_type: str

def extract_text_from_pdf(file_path):
    """Extract text from a PDF file."""
    try:
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text from PDF: {str(e)}")

def extract_text_from_docx(file_path):
    """Extract text from a DOCX file."""
    try:
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text from DOCX: {str(e)}")

def extract_key_criteria(text, criteria_type):
    """
    Use Gemini API to extract key criteria from job descriptions.
    
    Args:
        text (str): The text to extract criteria from
        criteria_type (str): The specific criteria type to extract
    """
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        # Handle 'overall' criteria type specially
        if criteria_type == 'overall':
            prompt = f"""
            Extract key ranking criteria (skills, experience, certifications, qualifications) 
            from the following job description.:
    
            {text}
            """
        else:
            prompt = f""" 
            Extract key criteria related to {criteria_type}  
            from the following job description. Return them as a list.
            Only include the actual criteria without any explanatory text or headings:

            {text} 
            """
        
        response = model.generate_content(prompt)
        
        # Process the response to get clean criteria items
        criteria_lines = [line.strip() for line in response.text.split("\n") if line.strip()]
        
        # Remove numbering and any extra spaces
        cleaned_criteria = []
        for line in criteria_lines:
            # Remove numbering (1., 2., etc.)
            if line[0].isdigit() and line[1:].startswith('. '):
                line = line[line.find('.')+1:].strip()
            # Remove bullet points if present
            if line.startswith('• '):
                line = line[2:].strip()
            if line.startswith('- '):
                line = line[2:].strip()
            if line:
                cleaned_criteria.append(line)
                
        return cleaned_criteria
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting criteria using Gemini: {str(e)}")

@app.post(
    "/extract-criteria", 
    response_model=CriteriaResponse,
    summary="Extract criteria from job description",
    description="""
    Upload a job description document (PDF or DOCX) and extract key criteria.
    
    Select what type of criteria to extract using the dropdown menu:
    - Choose "overall" for a comprehensive analysis of all important aspects
    - Select a specific criteria type for targeted analysis
    
    Returns a structured list of criteria extracted from the document.
    """
)
async def extract_criteria(
    file: UploadFile = File(..., description="PDF or DOCX file containing job description"),
    criteria_type: CriteriaType = Query(
        default=CriteriaType.overall,
        description="Select the type of criteria to extract from the job description"
    )
):
    # Validate file type
    if not file.filename.endswith(('.pdf', '.docx')):
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a PDF or DOCX file.")
    
    # Create temp directory if it doesn't exist
    os.makedirs("./temp", exist_ok=True)
    
    file_path = f"./temp/{file.filename}"
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Extract text based on file type
        if file.filename.endswith(".pdf"):
            text = extract_text_from_pdf(file_path)
        else:  # .docx
            text = extract_text_from_docx(file_path)
        
        if not text or text.isspace():
            raise HTTPException(status_code=422, detail="Could not extract any text from the provided file. Please check the file content.")

        # Convert enum value to string
        criteria_type_str = criteria_type.value
        
        # Extract criteria using Gemini
        criteria = extract_key_criteria(text, criteria_type_str)
        
        if not criteria:
            raise HTTPException(status_code=404, detail="No criteria could be extracted from the provided document.")
        
        return {
            "criteria": criteria,
            "criteria_type": criteria_type_str
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    
    finally:
        # Clean up the temporary file
        if os.path.exists(file_path):
            os.remove(file_path)

@app.get(
    "/", 
    summary="API Root",
    description="Returns a welcome message and instructions for using the API."
)
def read_root():
    return {
        "message": "Job Description Analysis API is running!",
        "documentation": "Use /docs for Swagger UI and API documentation",
        "endpoints": {
            "extract_criteria": {
                "url": "/extract-criteria",
                "method": "POST",
                "description": "Upload a job description file to extract key criteria"
            }
        },
        "features": {
            "criteria_types": "Use the 'overall' option for comprehensive analysis, or select a specific criteria type"
        }
    }