# DermaCare AI

## AI-Powered Skin & Wound Triage Web Application

DermaCare AI is an advanced AI-powered medical triage platform that analyzes skin and wound images using computer vision and large language models. The application generates preliminary condition predictions, risk analysis, AI-generated medical reports, downloadable PDFs, and chatbot-based follow-up guidance.

---

# Features

- AI-based skin and wound image analysis
- Preliminary medical triage prediction
- Risk-level assessment system
- AI-generated clinical-style reports
- PDF medical report download
- Interactive medical chatbot assistant
- Modern responsive healthcare UI
- Real-time image upload and preview
- Confidence score generation
- Safety-focused medical disclaimer system

---

# Tech Stack

## Frontend

- React.js
- Vite
- CSS3
- Lucide React Icons
- jsPDF

## Backend

- FastAPI
- Python
- CLIP Model
- Transformers
- Torch
- Groq LLM API

---

# System Workflow

1. Upload a skin or wound image
2. AI model analyzes the image
3. CLIP predicts possible condition
4. Risk level and confidence are calculated
5. AI-generated triage report is created
6. PDF report becomes downloadable
7. Chatbot answers follow-up questions safely

---

# Project Architecture

```text
Frontend (React + Vite)
        ↓
FastAPI Backend
        ↓
CLIP Image Analysis Model
        ↓
Groq LLM Report Generation
        ↓
PDF + Chatbot Output
```

---

# Installation Guide

## Clone Repository

```bash
git clone https://github.com/Nandan0201-debug/dermacare-ai.git
```

---

# Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on:

```text
http://localhost:5173
```

---

# Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend runs on:

```text
http://127.0.0.1:8000
```

---

# Environment Variables

Create a `.env` file inside backend folder.

```env
GROQ_API_KEY=your_api_key_here
```

---

# API Endpoints

## Analyze Image

```http
POST /analyze
```

Uploads image and generates AI triage report.

---

## Chat Assistant

```http
POST /chat
```

Handles follow-up chatbot interactions.

---

# Screenshots

## Landing Page
Add screenshot here

## Analysis Dashboard
Add screenshot here

## PDF Report
Add screenshot here

---

# Future Improvements

- Live webcam analysis
- Real-time doctor consultation
- Voice-enabled AI assistant
- Cloud database integration
- Medical history tracking
- Multi-language support
- AI wound healing tracking

---

# Deployment

## Frontend
- Vercel

## Backend
- Render

---

# Disclaimer

This project provides AI-assisted preliminary guidance only and is not a replacement for professional medical diagnosis or treatment.

---

# Author

## Jothisk Nandan Palla

GitHub:
https://github.com/Nandan0201-debug

LinkedIn:
https://linkedin.com/in/palla-jothisk-nandan

---

# License

This project is developed for educational, research, and portfolio purposes.