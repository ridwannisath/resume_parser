# ⟪ RESUME_PARSER_CORE ⟫

> **SYSTEM STATUS:** ONLINE
> **PROTOCOL:** CANDIDATE_DATA_EXTRACTION
> **AI CORE:** GEMINI-1.5-FLASH [ACTIVE]

---

## // MISSION BRIEFING

Welcome to the **Resume Parser Core**, a high-velocity data extraction engine designed to transmute unstructured document data into crystalline intelligence. Leveraging the symbiotic union of **Deterministic Algorithms (Regex)** and **Generative Neural Networks (Gemini AI)**, this system ingests biological profile documents (Resumes) and outputs structured digital entities.

## // SYSTEM CAPABILITIES

*   **[HYBRID_ANALYSIS_ENGINE]**
    *   **Text Documents (PDF/DOCX):** Scanned by high-speed regex pattern matchers for instant data stripping.
    *   **Visual Inputs (IMG/PNG/JPG):** Processed by **Google Gemini Vision**, a state-of-the-art neural interface capable of "reading" pixels like code.
*   **[DUPLICATION_SENTINEL]**
    *   Autonomous scanning for redundant biological entities. Prevents database fragmentation by merging data streams based on unique identifiers (Email/Phone).
*   **[HOLOGRAPHIC_DASHBOARD]**
    *   Visual interface for human operators to monitor, query, and export parsed intelligence.
*   **[UNIVERSAL_COMPATIBILITY]**
    *   Ingests multiple formats: `.pdf`, `.docx`, `.jpg`, `.png`, `.webp`.

## // ARCHITECTURAL BLUEPRINT

| COMPONENT | SPECIFICATION |
| :--- | :--- |
| **Mainframe** | Python 3.x / Flask Microframework |
| **Neural Engine** | Google Gemini Generative AI |
| **Memory Bank** | SQLite (Local) / PostgreSQL (Cloud Node) |
| **Optical Modules** | `pdfplumber`, `python-docx`, `Pillow` |
| **Visual Interface** | HTML5 / Bootstrap 5 / Jinja2 |

## // INITIALIZATION SEQUENCE

To deploy the system on your local node, execute the following command directives:

### 1. CLONE_REPOSITORY
```bash
git clone <secure-uplink-url>
cd resume_parser
```

### 2. ENGAGE_VIRTUAL_ENVIRONMENT
```bash
# Windows Terminal
python -m venv venv
venv\Scripts\activate

# Unix / MacOS Terminal
python3 -m venv venv
source venv/bin/activate
```

### 3. INJECT_DEPENDENCIES
```bash
pip install -r requirements.txt
```

### 4. CONFIGURE_NEURAL_LINK
The system requires a **Google API Key** to power the Gemini Vision module.
*   *WARNING:* Default key is hardcoded for demonstration. For secure operations, inject environment variable:
```bash
$env:GOOGLE_API_KEY = "YOUR_SECURE_KEY"
```

## // EXECUTION PROTOCOL

1.  **IGNITE SYSTEM:**
    ```bash
    python app.py
    ```
    > *Console Output: System listening on port 5000...*

2.  **ESTABLISH CONNECTION:**
    Navigate your web browser to `http://127.0.0.1:5000`.

3.  **INITIATE PARSING:**
    *   **UPLOAD:** Select target files via the interface.
    *   **PROCESS:** Engage the extraction algorithm.
    *   **ANALYZE:** Review the structured output on the Dashboard.

## // DEPLOYMENT VECTORS

Prepared for orbital launch via **Render** or **Heroku**.
*   **Procfile:** DETECTED.
*   **Environment Config:** `DATABASE_URL` & `GOOGLE_API_KEY` required for cloud synchronization.

## // LICENSE
Open Source Initiative. [MIT License](LICENSE).

---
*END OF TRANSMISSION.*
