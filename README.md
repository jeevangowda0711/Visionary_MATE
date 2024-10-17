# 🎯 **Visionary_MATE** - Blind Assistance & Multimodal Interaction Platform

Welcome to **Visionary_MATE**, a powerful and innovative platform designed to assist visually impaired individuals with AI-driven navigation and multimodal interaction capabilities. This platform integrates **AI-powered conversational systems**, **image processing**, **document extraction**, **audio input**, and **geolocation** technologies to provide seamless assistance to users.

## 🌟 **Features**

### 🦻 **Voice-Only Navigation (Visionary)**
- **Voice Commands**: Users can provide audio input for navigation and query processing.
- **Real-Time Geolocation**: The system leverages the **Mapbox API** to provide step-by-step navigation based on real-time GPS coordinates.
- **Shake Detection**: Allows users to start interactions by shaking the device, making it accessible for the visually impaired.
- **Auditory Feedback**: Offers spoken feedback using **Google Cloud Text-to-Speech** for confirming actions and providing responses.

### 🖼️ **Multimodal Interaction (Multimodal Mate)**
- **File Upload & Processing**: Upload and process various file types such as PDFs, DOCX, and images. The system uses **pytesseract** for Optical Character Recognition (OCR) and document extraction.
- **RAG (Retrieval-Augmented Generation) Pipeline**: Combines **HuggingFace embeddings** and **Google Gemini AI** to generate conversational responses based on uploaded documents.
- **Audio, Image, Video Processing**: Handles and processes media files (images, audio, video) using the **Google Gemini Flash model** to extract meaningful content or provide analysis.

### 📜 **File Types Supported**
- **PDF**: Text extraction from PDF files using `PyPDF2`.
- **DOCX**: Extracts text from Word documents using `python-docx`.
- **Images**: Uses `pytesseract` for OCR on image files.
- **Audio/Video Files**: Analyzes multimedia files using the **Google Gemini Flash model**.

### 🧠 **AI-Powered Responses**
- **Google Gemini Model Integration**: Provides natural language processing (NLP) and conversational abilities using Google's **Gemini model** for generating responses and analyzing media.
- **LLM-based RAG Pipeline**: Leverages **Llama-Index** and **HuggingFace Embeddings** to answer questions using uploaded documents, making it an ideal system for multimodal input.

### 🌍 **Real-Time Location Assistance**
- **Geolocation Integration**: Fetches real-time GPS data and delivers step-by-step navigation assistance using the **Mapbox API**.
- **Voice-Activated Navigation**: Users can ask for directions, and the system will return detailed voice-based guidance to the nearest destination.

---

## ⚙️ **Technology Stack**

- **Backend**: FastAPI, for building high-performance APIs with Python.
- **Frontend**: HTML, CSS (via Tailwind CSS), and JavaScript for building the user interface.
- **AI & NLP**: Powered by **Google Gemini Model**, **HuggingFace Sentence Transformers**, and **Llama-Index** for multimodal data processing and response generation.
- **Audio Processing**: Integrated with **Google Cloud Text-to-Speech** and **Pydub** for handling audio input and output.
- **Geolocation**: The **Mapbox API** is used to provide accurate geolocation-based services.
- **Document Processing**: `pytesseract` for OCR, `PyPDF2` for PDFs, and `python-docx` for Word documents.
  
---

## 🚀 **How to Run the Project**

1. **Clone the repository**:
    ```bash
    git clone https://github.com/jeevangowda0711/Visionary_MATE.git
    cd Visionary_MATE
    ```

2. **Install Dependencies**:
    Ensure you have Python 3.8+ installed. Run the following command to install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

3. **Set up Environment Variables**:
    Create a `.env` file and include the following keys:
    ```bash
    GOOGLE_API_KEY=<Your Google API Key>
    MAPBOX_API_KEY=<Your Mapbox API Key>
    GOOGLE_APPLICATION_CREDENTIALS=<Path to your Google Cloud credentials JSON>
    ```

4. **Run the Application**:
    Start the FastAPI application:
    ```bash
    uvicorn main:app --reload
    ```

5. **Access the Application**:
    Open your browser and go to `http://127.0.0.1:8000/` to access the app.

---

## 📁 **Directory Structure**
```bash
Visionary_MATE/
├── main.py                       # Main FastAPI app
├── multimodal_mate/               # Multimodal Mate's backend
│   ├── static/                    # Static assets for Multimodal Mate
│   ├── templates/                 # Frontend templates for Multimodal Mate
│   └── mate.py                    # FastAPI router and logic for Mate system
├── visionary/                     # Visionary's backend
│   ├── static/                    # Static assets for Visionary
│   ├── templates/                 # Frontend templates for Visionary system
│   └── visionary.py               # FastAPI router and logic for Visionary system
├── static/                        # Shared static files (JS, CSS)
├── templates/                     # Shared HTML templates
├── requirements.txt               # Python dependencies
└── .env                           # Environment variables (not included in repo)
```

---

## 🛠️ **Technologies Used**
- **FastAPI**: Backend framework for building scalable APIs.
- **Llama-Index**: Used for document indexing and querying in the Retrieval-Augmented Generation (RAG) pipeline.
- **Google Gemini AI**: Provides AI-powered conversational abilities and media analysis.
- **Mapbox API**: Delivers real-time geolocation and navigation capabilities.
- **Pytesseract**: Extracts text from images (OCR).
- **Google Cloud Text-to-Speech**: Converts responses into synthesized speech.
- **HuggingFace Embeddings**: Enables semantic search and document similarity checks using pre-trained models.

---

## 📄 **License**
This project is licensed under the MIT License.

---
