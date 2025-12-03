import os
import re
import json
import pandas as pd
import pdfplumber
import google.generativeai as genai
from docx import Document
from PIL import Image
import pytesseract
from flask import Flask, render_template, request, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'png', 'jpg', 'jpeg', 'webp'}

# --- PASTE YOUR GOOGLE API KEY BELOW ---
os.environ["GOOGLE_API_KEY"] = "AIzaSyALSVRbVKrV8OUNum-MCyxALpoX7jZh9R4"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Initialize Gemini Model
model = genai.GenerativeModel('gemini-1.5-flash')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///resumes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    location = db.Column(db.String(100)) # Gemini often finds location
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    pass
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
    if re.match(r'^[A-Z][A-Z\s\.]{2,}$', line):
      return line.title()
# 2. Initial + Name (M DINAGAR)
  for line in lines[:10]:
    if re.match(r'^[A-Z]\.?( )?[A-Z][a-zA-Z]+$', line):
      return line.title()
  # 3. Name + Initial (Saranraj M)
  for line in lines[:10]:
    if re.match(r'^[A-Z]\.?( )?[A-Z][a-zA-Z]+$', line):
      return line.title()
  # 4. Two-word name
  for line in lines[:10]:
    if re.match(r'^[A-Z][a-zA-Z]+ [A-Z][a-zA-Z]+$', line):
      return line.strip()

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
        r'b\.?tech', r'b\.?e', r'm\.?tech', r'm\.?e',
        r'bachelor', r'master'
    ]
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            return match.group(0).upper()
    return ""

def extract_department(text):
    # Find education section specifically for better accuracy
    txt_lower = text.lower()
    edu_section = text
    keywords = ["education", "academic details", "qualification", "educational qualification"]
    for key in keywords:
        if key in txt_lower:
            start = txt_lower.index(key)
            edu_section = text[start:start + 800]
            break
            
    patterns = [
        r"electronics and communication", r"computer science", r"information technology",
        r"electrical and electronics", r"mechanical engineering", r"civil engineering", 
        r"artificial intelligence and data science", r"computer science and engineering", 
        r"data science", r"artificial intelligence", r"cyber security", r"ECE", r"CS", r"IT",
        r"EEE", r"MECH", r"CIVIL", r"AI&DS", r"CSE", r"DS", r"AI", r"CYS"
    ]
    for p in patterns:
        if re.search(p, edu_section, re.IGNORECASE):
            return p.title()
    return "Not Specified"

def extract_state(text):
    # List of States (You can add more)
    states = [
        "Tamil Nadu", "Tamilnadu", "Kerala", "Karnataka", "Andhra Pradesh",
        "Telangana", "Maharashtra", "Delhi", "Puducherry", "Uttar Pradesh",
        "West Bengal", "Gujarat", "Rajasthan","TN","AP"
    ]
    for state in states:
        # Search whole text as address can be anywhere
        if re.search(r'\b' + re.escape(state) + r'\b', text, re.IGNORECASE):
            return state.title()
    return "Not Specified"

def extract_district(text):
    # List of Districts/Cities (Focused on TN/South + Major Metros)
    districts = [
        "Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Trichy", "Salem",
        "Tirunelveli", "Erode", "Vellore", "Thoothukudi", "Ramanathapuram",
        "Dindigul", "Thanjavur", "Virudhunagar", "Karur", "Nilgiris", "Krishnagiri",
        "Kanyakumari", "Namakkal", "Theni", "Sivaganga", "Tiruppur", 
        "Tiruvallur", "Kancheepuram", "Chengalpattu", "Cuddalore",
        "Bangalore", "Bengaluru", "Hyderabad", "Kochi", "Cochin", 
        "Thiruvananthapuram", "Trivandrum", "Mumbai", "Pune", "Kolkata", "New Delhi"
    ]
    for dist in districts:
        if re.search(r'\b' + re.escape(dist) + r'\b', text, re.IGNORECASE):
            return dist.title()
    return "Not Specified"

def extract_year_of_passing(text):
    matches = re.findall(r'(?:20\d{2})[\s\-\–]+(\d{2,4})', text)
    if matches:
        return max(matches)
    return "Not Specified"



def parse_with_regex(filepath):
    """Orchestrates the Traditional Parsing"""
    raw_text = extract_text_traditional(filepath)
    # Clean OCR artifacts if any (simple cleanup)
    raw_text = raw_text.replace("■", "").replace("●", "")
    
    return {
        "Name": extract_name(raw_text),
        "Email": extract_email(raw_text),
        "Phone": extract_phone(raw_text),
        "College": extract_college(raw_text),
        "Degree": extract_degree(raw_text),
        "Department": extract_department(raw_text),
        "Year": extract_year_of_passing(raw_text),
        "State": extract_state(raw_text),
        "District": extract_district(raw_text)
    }

# ==========================================
# PART 2: GEMINI AI LOGIC (FOR IMAGES)
# ==========================================

def parse_with_gemini(file_path):
    """Sends image to Gemini for analysis"""
    try:
        img = Image.open(file_path)
        prompt = """
        You are an expert Resume Parser. Analyze this resume image and extract the following details.
        Return ONLY a valid JSON object. Do not write markdown formatting.
        Fields to extract:
        - Name 
        - Contact (Phone number)
        - Email
        - College
        - Degree 
        - Department 
        - Location 
        - Passed Out (Year of graduation)
        If a value is not found, use "Not Specified".
        """
        response = model.generate_content([prompt, img])
        clean_text = response.text.strip()
        # Clean markdown code blocks if AI adds them
        if clean_text.startswith("```json"): clean_text = clean_text[7:]
        if clean_text.endswith("```"): clean_text = clean_text[:-3]
        
        data = json.loads(clean_text)
        
        return {
            "Name": data.get("Name", "Not Specified"),
            "Email": data.get("Email", "Not Specified"),
            "Phone": data.get("Contact", "Not Specified"),
            "College": data.get("College", "Not Specified"),
            "Degree": data.get("Degree", "Not Specified"),
            "Department": data.get("Department", "Not Specified"),
            "Year": data.get("Passed Out", "Not Specified"),
            "Location": data.get("Location", "Not Specified")
        }
    except Exception as e:
        print(f"Gemini Error: {e}")
        return None

# ==========================================
# ROUTES
# ==========================================
with app.app_context():
    db.create_all()
    print("Database tables created successfully!")


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
            
            # --- STRICT SEPARATION LOGIC ---
            ext = filename.rsplit('.', 1)[1].lower()
            
            if ext in ['pdf', 'docx']:
                # 1. Execute TRADITIONAL REGEX CODE
                print(f"Processing {filename} with REGEX...")
                data = parse_with_regex(filepath)
            
            elif ext in ['png', 'jpg', 'jpeg', 'webp']:
                # 2. Execute GEMINI AI CODE
                print(f"Processing {filename} with GEMINI...")
                data = parse_with_gemini(filepath)
            
            else:
                data = None

            if data:
                # Save to Database
                new_candidate = Candidate(
                    filename=filename,
                    name=data['Name'],
                    email=data['Email'],
                    phone=data['Phone'],
                    college=data['College'],
                    degree=data['Degree'],
                    department=data['Department'],
                    state=data.get('State', ''),
                    district=data.get('District', ''),
                    year_passing=data['Year'],
                )
                db.session.add(new_candidate)
    
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    candidates = Candidate.query.order_by(Candidate.upload_date.desc()).all()
    return render_template('dashboard.html', candidates=candidates)

# --- EXPORTS ---
@app.route('/export/excel')
# <--- Make sure this matches the HTML link
def export_excel():
    candidates = Candidate.query.all()
    # Logic to create excel...
    data = []
    for c in candidates:
        data.append({
        "Name": c.name, 
        "Contact": c.phone, 
        "Email": c.email,
        "Degree": c.degree, 
        "Department": c.department, 
        "College": c.college, 
        "State": c.state,         # Ensure these are included
        "District": c.district,   # Ensure these are included
        "Passed Out": c.year_passing, 
        "File Name": c.filename
    })
    
    df = pd.DataFrame(data)
    filename = "Resume_Data_Detailed.xlsx"
    df.to_excel(filename, index=False)
    return send_file(filename, as_attachment=True)

@app.route('/export/json')
def export_json():
    candidates = Candidate.query.all()
    data = [{
        "Name": c.name, "Contact": c.phone, "Email": c.email, 
        "Degree": c.degree, "Department": c.department,
        "College": c.college,
        "State": c.state, "District": c.district,
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

