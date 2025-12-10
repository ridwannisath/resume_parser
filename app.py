import os
import re
import json
import pandas as pd
import pdfplumber
import google.generativeai as genai
from docx import Document
from PIL import Image
from flask import Flask, render_template, request, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'png', 'jpg', 'jpeg', 'webp'}

# API Configuration
# Note: In production, it is safer to use os.getenv("GOOGLE_API_KEY")
os.environ["GOOGLE_API_KEY"] = "AIzaSyCtzhOhQbCldyfmA8JRO241L4pFZB6vtsE"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- DATABASE CONFIGURATION (UPDATED FOR POSTGRESQL) ---
# Get the URL from the environment (Render sets this) or use SQLite as a backup for local testing
database_url = os.environ.get('DATABASE_URL', 'sqlite:///resumes.db')

# Fix for Render's URL format (postgres:// -> postgresql://)
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# -------------------------------------------------------

db = SQLAlchemy(app)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==========================================
# DATABASE MODEL
# ==========================================
class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(150))
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    college = db.Column(db.String(200))
    degree = db.Column(db.String(100))
    department = db.Column(db.String(100))
    state = db.Column(db.String(50))
    district = db.Column(db.String(50))
    year_passing = db.Column(db.String(20))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
# --- CRITICAL: CREATE TABLES ON STARTUP ---
# This ensures tables exist before any request is made
with app.app_context():
    db.create_all()
    print("Database connected and tables verified.")

# ==========================================
# PART 1: TRADITIONAL REGEX LOGIC (FOR PDF/DOCX)
# ==========================================

def extract_text_traditional(file_path):
    ext = file_path.rsplit('.', 1)[1].lower()
    text = ""
    try:
        if ext == 'pdf':
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += (page.extract_text() or "") + "\n"
        elif ext == 'docx':
            doc = Document(file_path)
            text = "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        print(f"Error reading document: {e}")
    return text

def extract_name(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # 1. ALL CAPS names
    for line in lines[:10]:
        if re.match(r'^[A-Z][A-Z\s\.]{2,}$', line): return line.title()
    # 2. Initial + Name
    for line in lines[:10]:
        if re.match(r'^[A-Z]\.?( )?[A-Z][a-zA-Z]+$', line): return line.title()
    # 3. Name + Initial
    for line in lines[:10]:
        if re.match(r'^[A-Z]\.?( )?[A-Z][a-zA-Z]+$', line): return line.title()
    # 4. Two-word name
    for line in lines[:10]:
        if re.match(r'^[A-Z][a-zA-Z]+ [A-Z][a-zA-Z]+$', line): return line.strip()
    return "Unknown"

def extract_email(text):
    m = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return m.group(0) if m else "Not Specified"

def extract_phone(text):
    m = re.search(r'\b(?:\+?91)?\s*\d{10}\b', text)
    return m.group(0) if m else "Not Specified"

def extract_college(text):
    m = re.search(r'([A-Za-z ]+(University|Institute|College))', text, re.IGNORECASE)
    return m.group(0).strip() if m else "Not Specified"

def extract_degree(text):
    patterns = [
            # Engineering UG/PG
            r'b\.?tech', r'b\.?e', r'm\.?tech', r'm\.?e',

            # Generic Bachelor/Master Words
            r'bachelor(?: of)?', r'master(?: of)?',

            # Science
            r'b\.?sc', r'm\.?sc',

            # Arts & Humanities
            r'b\.?a', r'm\.?a',

            # Commerce / Business
            r'b\.?com', r'm\.?com', r'b\.?ba', r'm\.?ba',

            # Computer Applications
            r'b\.?ca', r'm\.?ca',

            # Education
            r'b\.?ed', r'm\.?ed',

            # Pharmacy
            r'b\.?pharm', r'm\.?pharm',

            # Architecture
            r'b\.?arch', r'm\.?arch',

            # Medical & Dental
            r'b\.?ds', r'm\.?ds', r'mbbs', r'bams', r'bhms',

            # Vocational Studies
            r'b\.?voc', r'm\.?voc',

            # Diplomas
            r'diploma', r'pg diploma',

            # Research
            r'ph\.?d', r'doctorate',
        ]

    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match: return match.group(0).upper()
    return "Not Specified"

def extract_department(text):
    txt_lower = text.lower()
    edu_section = text
    keywords = ["education", "academic details", "qualification", "educational qualification"]
    for key in keywords:
        if key in txt_lower:
            start = txt_lower.index(key)
            edu_section = text[start:start + 1000]
            break
            
    patterns = [
        # Engineering & Technology
        r"electronics and communication", r"electronic communication", r"ece",
        r"computer science", r"cs", r"cse",
        r"electrical and electronics", r"eee",
        r"mechanical engineering", r"mech",
        r"civil engineering", r"civil",
        r"artificial intelligence and data science", r"ai&ds",
        r"data science", r"data analytics",
        r"artificial intelligence", r"ai",
        r"artificial intelligence and data science", r"AI&DS",
        r"cyber security", r"cybersecurity",
         r"information technology", r"it",
        
        # Other Science Departments
        r"physics", r"chemistry", r"biology", r"biotechnology",
        r"mathematics", r"statistics", r"environmental science",

        # Business & Commerce fields
        r"accounting", r"finance", r"banking", r"insurance",
        r"business administration", r"bba",
        r"marketing", r"human resource", r"hr",
        r"international business", r"operations management",

        # Arts & Humanities
        r"english", r"literature", r"history", r"political science",
        r"psychology", r"sociology", r"fine arts", r"design",
        r"journalism", r"mass communication",

        # Professional Domains
        r"computer applications", r"ca",
        r"education", r"teaching",
        r"pharmacy",
        r"law", r"legal studies",
        ]
    for p in patterns:
        if re.search(p, edu_section, re.IGNORECASE): return p.title()
    return "Not Specified"

def extract_state(text):
    states = ["Tamil Nadu", "Tamilnadu", "Kerala", "Karnataka", "Andhra Pradesh", "Telangana", "Maharashtra", "Delhi"]
    for state in states:
        if re.search(r'\b' + re.escape(state) + r'\b', text, re.IGNORECASE): return state.title()
    return "Not Specified"

def extract_district(text):
    districts = [ 
            r"ariyalur",
            r"chengalpattu",
            r"chennai",
            r"coimbatore",
            r"cuddalore",
            r"dharmapuri",
            r"dindigul",
            r"erode",
            r"kallakurichi",
            r"kancheepuram",
            r"karur",
            r"krishnagiri",
            r"madurai",
            r"mayiladuthurai",
            r"nagapattinam",
            r"namakkal",
            r"nilgiris", r"the nilgiris",
            r"perambalur",
            r"pudukkottai",
            r"ramanathapuram",
            r"ranipet",
            r"salem",
            r"sivagangai",
            r"tenkasi",
            r"thanjavur",
            r"theni",
            r"thiruvallur",
            r"thiruvarur",
            r"thoothukudi", r"tuticorin",
            r"tiruchirappalli", r"trichy",
            r"tirunelveli",
            r"tirupathur",
            r"tiruppur",
            r"tiruvannamalai",
            r"vellore",
            r"viluppuram",
            r"virudhunagar",
            r"kanyakumari"
        ]
    for dist in districts:
        if re.search(r'\b' + re.escape(dist) + r'\b', text, re.IGNORECASE): return dist.title()
    return "Not Specified"

def extract_year_of_passing(text):
    # 1. Robust Logic for Range (2020-2024)
    pattern_range = r'(20\d{2})\s*[\-\–]\s*(\d{2,4})'
    match_range = re.search(pattern_range, text)
    if match_range:
        end_year = match_range.group(2)
        if len(end_year) == 2: return "20" + end_year 
        return end_year

    # 2. Fallback: Max Year
    matches = re.findall(r'\b(20\d{2})\b', text)
    valid_years = [int(y) for y in matches if 2000 <= int(y) <= 2030]
    if valid_years: return str(max(valid_years))
    
    return "Not Specified"

def parse_with_regex(filepath):
    raw_text = extract_text_traditional(filepath)
    raw_text = raw_text.replace("■", "").replace("●", "")
    return {
        "Name": extract_name(raw_text),
        "Email": extract_email(raw_text),
        "Phone": extract_phone(raw_text),
        "College": extract_college(raw_text),
        "Degree": extract_degree(raw_text),
        "Department": extract_department(raw_text),
        "Passed Out": extract_year_of_passing(raw_text),
        "State": extract_state(raw_text),
        "District": extract_district(raw_text)
    }

# ==========================================
# PART 2: GEMINI AI LOGIC (FOR IMAGES)
# ==========================================
def extract_data_with_gemini(file_path):

    if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        img = Image.open(file_path)

        prompt = """
         You are an expert Resume Parser. Analyze this resume image and extract the following details.
        Return ONLY a valid JSON object. Do not write markdown formatting.
        Fields to extract:
        - Name 
        - Phone (without country code, can be 10 digit number or with country code +91 XXXXXXXXXX)
        - Email
        - College
        - Degree (only highest degree, e.g., B.Tech, M.Tech, B.E, M.E, Bachelor, Master)
        - Department
        - district
        - state
        - Passed Out (Year of graduation)
        If a value is not found, use "Not Specified".
        """
        try:
            response = model.generate_content([prompt, img])
            clean = response.text.strip()

            # Remove Markdown fences if present
            clean = clean.replace("```json", "").replace("```", "").strip()

            return json.loads(clean)

        except Exception as e:
            print("\n❌ Gemini JSON Parsing Failed")
            print("Raw Output:\n", response.text if 'response' in locals() else "No response")
            print("Error:", e)
            return None

    else:
        return {"Name": "File format not supported"}


# ==========================================
# ROUTES
# ==========================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files[]' not in request.files: return redirect(request.url)
    files = request.files.getlist('files[]')
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            ext = filename.rsplit('.', 1)[1].lower()
            data = None
            
            if ext in ['pdf', 'docx']:
                print(f"Processing {filename} with REGEX...")
                data = parse_with_regex(filepath)
            
            elif ext in ['png', 'jpg', 'jpeg', 'webp']:
                print(f"Processing {filename} with GEMINI...")
                data = extract_data_with_gemini(filepath)
                
# ---------------------------------------------------------
# DUPLICATE DETECTION AND UPDATE LOGIC
# ---------------------------------------------------------
            if data:
                email_extracted = data.get('Email')
                phone_extracted = data.get('Phone')
                
                existing_candidate = None

                # 1. Check by Email (if valid)
                if email_extracted and email_extracted.lower() != "not specified":
                    existing_candidate = Candidate.query.filter_by(email=email_extracted).first()
                
                # 2. Check by Phone (if valid and not found by email yet)
                if not existing_candidate and phone_extracted and phone_extracted != "not specified":
                    existing_candidate = Candidate.query.filter_by(phone=phone_extracted).first()
                
                if existing_candidate:
                    # --- UPDATE EXISTING RECORD ---
                    print(f"Duplicate found for {existing_candidate.name}. Updating record...")
                    existing_candidate.filename = filename
                    existing_candidate.name = data.get('Name') or "Not Specified"
                    existing_candidate.email = email_extracted or "Not Specified"
                    existing_candidate.phone = phone_extracted or "Not Specified"
                    existing_candidate.college = data.get('College') or "Not Specified"
                    existing_candidate.degree = data.get('Degree') or "Not Specified"
                    existing_candidate.department = data.get('Department') or "Not Specified"
                    existing_candidate.year_passing = data.get('Passed Out') or "Not Specified"
                    existing_candidate.state = data.get('State') or "Not Specified"
                    existing_candidate.district = data.get('District') or "Not Specified"
                    existing_candidate.upload_date = datetime.utcnow() # Update timestamp
                else:
                    # --- INSERT NEW RECORD ---
                    print(f"Creating new record for {data.get('Name')}...")
                    new_candidate = Candidate(
                        filename=filename,
                        name=data.get('Name') or "Not Specified",
                        email=email_extracted or "Not Specified",
                        phone=phone_extracted or "Not Specified",
                        college=data.get('College') or "Not Specified",
                        degree=data.get('Degree') or "Not Specified",
                        department=data.get('Department') or "Not Specified",
                        year_passing=data.get('Passed Out') or "Not Specified",
                        state=data.get('State') or "Not Specified",
                        district=data.get('District') or "Not Specified"
                    )
                    db.session.add(new_candidate)
    
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    candidates = Candidate.query.order_by(Candidate.upload_date.desc()).all()
    return render_template('dashboard.html', candidates=candidates)

@app.route('/export/json')
def export_json():
    candidates = Candidate.query.all()
    data = [{
        "Name": c.name, "Contact": c.phone, "Email": c.email, 
        "Degree": c.degree, "Department": c.department,
        "College": c.college, "State": c.state, "District": c.district,
        "Passed Out": c.year_passing, "File Name": c.filename
    } for c in candidates]
    
    filename = "Resume_Data_Detailed.json"
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

