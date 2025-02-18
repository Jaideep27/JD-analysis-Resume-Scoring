from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pdfplumber
import docx
import pandas as pd
import google.generativeai as genai
import os
from typing import List, Dict
import json
from datetime import datetime
import shutil
from pydantic import BaseModel
from dotenv import load_dotenv

app = FastAPI(
    title="Resume Scoring API",
    description="API for detailed resume evaluation against multiple criteria",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Config:
    UPLOAD_DIR = "temp/uploads"
    OUTPUT_DIR = "temp/output"
    ALLOWED_EXTENSIONS = {".pdf", ".docx"}
    MAX_SCORE = 5

    @classmethod
    def initialize(cls):
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)

Config.initialize()
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")
genai.configure(api_key=GEMINI_API_KEY)

class TextExtractor:
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        try:
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text.strip()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error extracting PDF: {str(e)}"
            )

    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        try:
            doc = docx.Document(file_path)
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error extracting DOCX: {str(e)}"
            )

    @classmethod
    def extract_text(cls, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return cls.extract_text_from_pdf(file_path)
        elif ext == ".docx":
            return cls.extract_text_from_docx(file_path)
        else:
            raise HTTPException(
                status_code=400, detail=f"Unsupported file format: {ext}"
            )

class ResumeScorer:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-pro")

    def create_detailed_prompt(self, text: str, criteria_list: List[str]) -> str:
        formatted_criteria = "\n".join(f"- {criterion}" for criterion in criteria_list)
        return f"""
        You are an expert HR professional with extensive experience in technical hiring. 
        Evaluate this resume against each criterion on a scale of 0-5.
        
        Scoring Guidelines:
        5 - Exceptional match
        4 - Strong match
        3 - Good match
        2 - Fair match
        1 - Poor match
        0 - No match
        
        Criteria to evaluate:
        {formatted_criteria}
        
        Resume Text:
        {text}
        
        Please provide the scores for each criterion in this exact format (maintain exact criterion names):
        {{
            {', '.join(f'"{criterion}": <score>' for criterion in criteria_list)}
        }}
        """

    def validate_score(self, score: int) -> int:
        return max(0, min(Config.MAX_SCORE, score))

    def parse_scores(self, response_text: str, criteria_list: List[str]) -> Dict[str, int]:
        try:
            # Clean the response text
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:-3].strip()
            
            # Parse the JSON response
            scores = json.loads(cleaned_text)
            
            # Create a dictionary with validated scores for each criterion
            validated_scores = {}
            for criterion in criteria_list:
                score = scores.get(criterion, 0)
                validated_scores[criterion] = self.validate_score(int(float(score)))
            
            return validated_scores
        except Exception as e:
            print(f"Error parsing scores: {e}")
            return {criterion: 0 for criterion in criteria_list}

    def score_resume(self, text: str, criteria_list: List[str]) -> Dict[str, int]:
        try:
            prompt = self.create_detailed_prompt(text, criteria_list)
            response = self.model.generate_content(prompt)
            if not response.text:
                raise ValueError("Empty response from model")
            return self.parse_scores(response.text, criteria_list)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Scoring error: {str(e)}")

class ResponseModel(BaseModel):
    message: str
    file_url: str
    total_processed: int
    timestamp: str

@app.post("/score-resumes/", response_model=ResponseModel)
async def score_resumes(
    criteria: str = Form(...),  # Accept as string and split later
    files: List[UploadFile] = File(...)
):
    if not criteria or not files:
        raise HTTPException(status_code=400, detail="Both criteria and files are required")

    # Split criteria into a list and clean each criterion
    criteria_list = [c.strip() for c in criteria.split(',')]
    
    scorer = ResumeScorer()
    results = []

    for file in files:
        if os.path.splitext(file.filename)[1].lower() not in Config.ALLOWED_EXTENSIONS:
            continue

        file_path = os.path.join(Config.UPLOAD_DIR, file.filename)
        try:
            # Save and process file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Extract text and get scores
            text = TextExtractor.extract_text(file_path)
            scores = scorer.score_resume(text, criteria_list)

            # Create result row with individual scores
            row = {
                "Candidate Name": os.path.splitext(file.filename)[0]
            }
            
            # Add each criterion score separately
            for criterion in criteria_list:
                row[criterion] = scores[criterion]
            
            # Add total score
            row["Total Score"] = sum(scores.values())
            
            results.append(row)

        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    if not results:
        raise HTTPException(status_code=500, detail="No files were processed successfully")

    # Create DataFrame with explicit column order
    df = pd.DataFrame(results)
    
    # Ensure columns are in the correct order
    columns = ["Candidate Name"] + criteria_list + ["Total Score"]
    df = df.reindex(columns=columns)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"resume_scores_{timestamp}.csv"
    output_path = os.path.join(Config.OUTPUT_DIR, output_filename)
    
    # Save to CSV with each criterion as a separate column
    df.to_csv(output_path, index=False)

    return ResponseModel(
        message="Processing complete",
        file_url=f"/download/{output_filename}",
        total_processed=len(results),
        timestamp=datetime.now().isoformat(),
    )

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(Config.OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename)