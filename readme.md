# JD analysis and Resume Ranking 🎯

An intelligent FastAPI application leveraging Google's Gemini-2.0 Flash model to automate resume evaluation and job description analysis. The system provides two main functionalities: job description criteria extraction and resume scoring.

## Project Structure 📁

```
resume-ranking-system/
├── __pycache__/
├── Job_Descriptions/        # Storage for job description files
├── Resumes/                 # Storage for resume files
├── task_1 (Sample_Outputs)/ # Sample outputs from task 1
├── task_2 (Sample_Outputs)/ # Sample outputs from task 2
├── temp/                    # Temporary file storage
├── .env                     # Environment variables 
├── requirements.txt         # Project dependencies 
├── task-1.py               # Job Description Analysis 
├── task-2.py               # Resume Scoring System 
└── readme.md               # Documentation
```

## Features ⚡

### 1. Job Description Analysis (task-1.py)
Extracts key ranking criteria from job descriptions using the Gemini-2.0 Flash model.

**API Endpoint:**
```http
POST /extract-criteria
```

**Input:**
- File (PDF/DOCX)
- Criteria Type (optional)

**Gemini Prompt Template:**
```python
# For overall analysis
"""
Extract key ranking criteria (skills, experience, certifications, qualifications) 
from the following job description.:

{text}
"""

# For specific criteria type
"""
Extract key criteria related to {criteria_type}  
from the following job description. Return them as a list.
Only include the actual criteria without any explanatory text or headings:

{text}
"""
```

### 2. Resume Scoring System (task-2.py)
Evaluates resumes against specified criteria using an AI-powered scoring system.

**API Endpoint:**
```http
POST /score-resumes
```

**Input:**
- Multiple resume files (PDF/DOCX)
- Criteria list (comma-separated)

**Gemini Prompt Template:**
```python
"""
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
{
    {', '.join(f'"{criterion}": <score>' for criterion in criteria_list)}
}
"""
```

## Installation 🚀

1. Clone the repository
```bash
git clone <repository-url>
cd JD analysis and Resume Ranking
```

2. Create virtual environment
```bash
python -m venv venv
source venv\Scripts\activate   
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
# Create .env file with your Gemini API key
GEMINI_API_KEY=your_api_key_here #(Not providing my key here)
```

## API Usage 💻

### Task 1: Extract Criteria
```python
import requests

url = "http://localhost:8000/extract-criteria"
files = {
    "file": ("job_description.pdf", open("job_description.pdf", "rb"))
}
params = {
    "criteria_type": "skills"  # Optional
}
response = requests.post(url, files=files, params=params)
print(response.json())
```

### Task 2: Score Resumes
```python
import requests

url = "http://localhost:8000/score-resumes"
files = [
    ("files", ("resume1.pdf", open("resume1.pdf", "rb"))),
    ("files", ("resume2.pdf", open("resume2.pdf", "rb")))
]
data = {
    "criteria": "Python,Machine Learning,Cloud Computing"
}
response = requests.post(url, files=files, data=data)
print(response.json())
```

## Sample Outputs 📊

### Task 1 Output (JSON)
```json
{
  "criteria": [
    "LLM Expertise",
    "RAG & Vector Databases",
    "Azure AI Services",
    "MLOps & CI/CD",
    "Database Proficiency",
    "Libraries & Frameworks"
  ],
  "criteria_type": "skills"
}
```

### Task 2 Output (CSV)
# Resume Scoring Results

| Candidate Name | BTech CSE Graduate | 6 months internship experience | Strong foundation in AI | Total Score |
|---------------|-------------------|------------------------------|----------------------|-------------|
| Charan        | 5                 | 4                           | 3                    | 12          |
| Ganesh        | 5                 | 0                           | 2                    | 7           |
| Ganga         | 5                 | 0                           | 2                    | 7           |
| Jaideep       | 5                 | 4                           | 4                    | 13          |
| Kowshik       | 5                 | 3                           | 4                    | 12          |
| Vivek         | 5                 | 1                           | 0                    | 6           |

## Running the Application 🚀

1. Start the servers:
```bash
# For Job Description Analysis
uvicorn task_1:app --reload

# For Resume Scoring
uvicorn task_2:app --reload 
```

2. Access Swagger Documentation:
- Task 1: http://localhost:8000/docs
- Task 2: http://localhost:8000/docs

## Error Handling 🛠️

The system handles various errors including:
- Invalid file formats
- File processing errors
- AI model errors
- Missing criteria
- File system operations

## Security Features 🔒

- Temporary file cleanup
- Input validation
- Secure file handling
- Environment variable protection
- CORS support


## Support 💬

For questions and support, please open an issue in the repository.