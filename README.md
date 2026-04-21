<h1 align="center">
  🧬 AI Integrative Multilingual Telehealth Orchestrator
</h1>

<p align="center">
  <strong>A Hybrid Clinical Decision Support & Care Navigation System</strong><br>
  Across Allopathic, Ayurvedic, Homeopathic, and Home-Remedial Practices
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-00C7B7?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Three.js-r128-black?logo=three.js&logoColor=white" alt="Three.js">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
</p>

---

## 🎯 Overview

The **AI Telehealth Orchestrator** is a production-ready, agentic AI system that processes patient symptoms through an **8-agent pipeline** to generate integrative, multi-modality care recommendations with full explainability and multilingual support.

It combines **modern allopathic medicine** with **traditional Ayurvedic practices**, performing automated triage, herb-drug safety checks, evidence-based recommendation synthesis, and provider-backed real-time translation into **6 Indian languages**.

### ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🧠 **8-Agent Pipeline** | Normalization → Triage → Orchestrator → Allopathy → Ayurveda → Safety → Synthesizer → Translation |
| 🌐 **Multilingual Input/Output** | Hindi, Tamil, Telugu, Bengali, Marathi + English with provider-backed translation and clinical fallback |
| 🛡️ **Safety Engine** | Herb-drug interaction checks, polypharmacy detection, pregnancy/age contraindications |
| 📊 **Evidence-Based** | Citations from WHO, ICMR, NICE, AYUSH, CCRAS, Cochrane with reliability tiers (A/B/T) |
| 🔍 **Explainability** | Full audit trace: risk factors, rule triggers, agent execution timeline |
| 🌿 **Dosha Assessment** | Vata/Pitta/Kapha analysis with dosha-aligned Ayurvedic formulations |
| 🎨 **3D Interactive UI** | Three.js particle network, glassmorphism design, animated pipeline visualization |
| 🐳 **Dockerized** | Single-command deployment with health checks |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Three.js + SPA)                    │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────────┐ │
│  │  Intake   │  │   Pipeline   │  │    Results Dashboard      │ │
│  │   Form    │──│  Animation   │──│  (Risk, Plans, Warnings,  │ │
│  │ (4 steps) │  │  (8 agents)  │  │   Evidence, Translations) │ │
│  └──────────┘  └──────────────┘  └───────────────────────────┘ │
└────────────────────────┬────────────────────────────────────────┘
                         │ REST API
┌────────────────────────┴────────────────────────────────────────┐
│                     FastAPI BACKEND                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Pipeline Orchestrator                    │ │
│  │                                                            │ │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌───────┐ ┌──────┐          │ │
│  │  │Norm. │→│Triage│→│Orch. │→│Allo.  │→│Ayur. │          │ │
│  │  └──────┘ └──────┘ └──────┘ │Spec.  │ │Spec. │          │ │
│  │                              └───────┘ └──────┘          │ │
│  │                                   │         │             │ │
│  │                              ┌────▼─────────▼───┐        │ │
│  │                              │   Safety Agent    │        │ │
│  │                              └────────┬─────────┘        │ │
│  │                              ┌────────▼─────────┐        │ │
│  │                              │   Synthesizer    │        │ │
│  │                              └────────┬─────────┘        │ │
│  │                              ┌────────▼─────────┐        │ │
│  │                              │   Translation    │        │ │
│  │                              └──────────────────┘        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Translation  │  │ Safety Rules │  │   Evidence Base      │  │
│  │ Provider/API │  │ (herb-drug)  │  │  (WHO/ICMR/CCRAS)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **pip** (included with Python)

### Option 1: Run Locally

```bash
# 1. Clone or navigate to the project
cd "Agentic AI Orchestrator"

# 2. Create and activate a virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# Optional: configure a real translation provider
# TRANSLATION_PROVIDER=azure
# TRANSLATOR_ENDPOINT=https://<your-resource>.cognitiveservices.azure.com
# TRANSLATOR_KEY=<your-key>
# TRANSLATOR_REGION=<your-region>

# 4. Start the server
uvicorn backend.main:app --host 127.0.0.1 --port 8000

# 5. Open in your browser
# → http://127.0.0.1:8000/
```

### Option 2: Run with Docker

```bash
# Build and start
docker-compose up --build

# The app will be available at:
# → http://localhost:8000/

# Stop
docker-compose down
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/intake` | Submit patient intake → runs full 8-agent pipeline |
| `GET` | `/api/status/{session_id}` | Check pipeline execution status |
| `GET` | `/api/recommendation/{session_id}` | Get full care recommendation (JSON) |
| `POST` | `/api/feedback` | Submit clinician feedback (approve/reject/edit) |
| `GET` | `/api/glossary/{lang_code}` | Get medical glossary for a language |
| `POST` | `/api/translate/text` | Translate arbitrary text snippets using the active translation provider |
| `GET` | `/api/languages` | List supported languages |
| `GET` | `/api/sessions` | List all active sessions |
| `GET` | `/api/audit` | View clinician feedback audit log |
| `GET` | `/api/health` | System health check |
| `GET` | `/docs` | Swagger UI (auto-generated API docs) |

### Example API Call

```bash
curl -X POST http://localhost:8000/api/intake \
  -H "Content-Type: application/json" \
  -d '{
    "age": 42,
    "sex": "F",
    "symptom_text": "Fever and headache for 3 days, joint pain",
    "duration_days": 3,
    "comorbidities": ["hypertension"],
    "medications": ["amlodipine"],
    "language_pref": "hi"
  }'
```

---

## 📁 Project Structure

```
Agentic AI Orchestrator/
├── backend/
│   ├── __init__.py
│   ├── config.py               # Centralized settings & feature flags
│   ├── main.py                 # FastAPI app + static file serving
│   ├── pipeline.py             # 8-agent orchestration + state management
│   ├── agents/
│   │   ├── normalization.py    # Symptom extraction (multilingual)
│   │   ├── triage.py           # Risk scoring (severity × age × comorbidity)
│   │   ├── orchestrator.py     # Modality routing + care path
│   │   ├── allopathy.py        # Evidence-based allopathic treatment (14 conditions)
│   │   ├── ayurveda.py         # Dosha-aligned Ayurvedic care (14 conditions)
│   │   ├── safety.py           # 6-check safety gate (herb-drug, polypharmacy, etc.)
│   │   ├── synthesizer.py      # Evidence-ranked plan merging + explainability
│   │   └── translation.py      # Provider-backed multilingual output with clinical fallback
│   ├── knowledge/
│   │   ├── glossary.py         # 60+ medical terms in 6 languages
│   │   ├── safety_rules.py     # Emergency detection, herb-drug interactions
│   │   └── evidence_base.py    # WHO, ICMR, NICE, AYUSH, CCRAS citations
│   └── schemas/
│       ├── common.py           # Core domain models & enums
│       ├── intake.py           # Patient intake validation
│       └── recommendation.py   # Final output schema + explainability
├── frontend/
│   ├── index.html              # SPA (intake form, pipeline viz, results)
│   ├── css/
│   │   └── styles.css          # Glassmorphism dark theme (700+ lines)
│   └── js/
│       ├── three-scene.js      # 3D particle network (Three.js)
│       └── app.js              # Form logic, API calls, results rendering
├── Dockerfile                  # Production container
├── docker-compose.yml          # Single-command deployment
├── .dockerignore
├── requirements.txt
└── README.md
```

---

## 🧪 Intelligent Rule-Based Simulation

This project uses **no external LLM API keys**. All 8 agents use robust, deterministic rule-based logic with realistic medical data:

- **Normalization**: Pattern-matched symptom extraction from free text in 6 languages
- **Triage**: Hybrid scoring model (severity × age × comorbidity × duration) with emergency fast-path
- **Allopathy**: 14-condition treatment database with comorbidity-aware prescribing
- **Ayurveda**: Dosha profiling (Vata/Pitta/Kapha) with 14-condition classical formulations
- **Safety**: Cross-referencing herb-drug interactions from curated knowledge base

> Translation: Set `TRANSLATION_PROVIDER=azure` and provide Azure Translator credentials to enable full sentence translation; otherwise the app falls back to the clinical glossary translator.

---

## 🛡️ Safety Features

- **Emergency Detection**: Automatic escalation for chest pain, stroke symptoms, breathing difficulty
- **Herb-Drug Interactions**: 6 known conflicts (e.g., Ashwagandha + sedatives, Guggulu + anticoagulants)
- **Ayurvedic Contraindications**: Dosha-specific restrictions for hypertension, renal disease, pregnancy
- **Polypharmacy Risk**: Alerts when total medication count exceeds safety thresholds
- **Pregnancy Screening**: Category X drug detection + Panchakarma contraindications
- **Allergy Cross-Reference**: Scans all plan segments against patient's known allergies

---

## 🌐 Supported Languages

| Code | Language | Script |
|------|----------|--------|
| `en` | English | Latin |
| `hi` | Hindi | देवनागरी |
| `ta` | Tamil | தமிழ் |
| `te` | Telugu | తెలుగు |
| `bn` | Bengali | বাংলা |
| `mr` | Marathi | मराठी |

---

## 📝 License

This project is licensed under the MIT License.

---

<p align="center">
  Built with ❤️ as a capstone AI Orchestrator project<br>
  <em>Integrating modern medicine with ancient wisdom, powered by agentic AI</em>
</p>
