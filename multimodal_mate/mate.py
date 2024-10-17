import os
import mimetypes
import base64
import tempfile
import traceback
import logging
from fastapi import APIRouter, File, UploadFile, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import pytesseract

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in the environment variables.")

# Configure the Google Generative AI (Gemini) API
genai.configure(api_key=GEMINI_API_KEY)

# Initialize the Gemini model
model = genai.GenerativeModel('gemini-pro')
vision_model = genai.GenerativeModel('gemini-pro-vision')

# Initialize the APIRouter
mate_router = APIRouter()
mate_templates = None

# Global dictionary to store document content
document_store = {}

class ChatRequest(BaseModel):
    message: str = Field(default="")
    file: str | None = Field(default=None)
    fileType: str | None = Field(default=None)

@mate_router.get("/", response_class=HTMLResponse)
async def mate_home(request: Request):
    return mate_templates.TemplateResponse("mate.html", {"request": request})

def detect_file_type(filename):
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"

def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(file_path):
    doc = Document(file_path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def extract_text_from_image(file_path):
    try:
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img)
        return text
    except pytesseract.TesseractNotFoundError:
        logger.error("Tesseract is not installed or not in PATH")
        return "Image text extraction is not available. Tesseract OCR is not installed."

@mate_router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    global document_store
    try:
        content = await file.read()
        file_type = detect_file_type(file.filename)
        logger.info(f"Uploading file: {file.filename} (Type: {file_type})")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = os.path.join(temp_dir, file.filename)
            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(content)

            if file_type == "application/pdf":
                extracted_text = extract_text_from_pdf(temp_file_path)
            elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                extracted_text = extract_text_from_docx(temp_file_path)
            elif file_type.startswith("image/"):
                extracted_text = extract_text_from_image(temp_file_path)
                if "Tesseract OCR is not installed" in extracted_text:
                    # If Tesseract is not available, store the image for vision model
                    with open(temp_file_path, "rb") as img_file:
                        document_store[file.filename] = {
                            "type": "image",
                            "content": base64.b64encode(img_file.read()).decode()
                        }
                    return JSONResponse(content={
                        "message": f"Image file stored for vision processing",
                        "filename": file.filename
                    })
            else:
                return JSONResponse(content={"message": "Unsupported file type"}, status_code=400)

        if extracted_text:
            document_store[file.filename] = {
                "type": "text",
                "content": extracted_text
            }
            logger.info(f"File processed and stored successfully: {file.filename}")
            return JSONResponse(content={
                "message": f"{file_type} file processed and stored successfully",
                "filename": file.filename,
                "content_preview": extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text
            })
        else:
            return JSONResponse(content={"message": "No content could be extracted from the file."}, status_code=400)

    except Exception as e:
        logger.error(f"Error in upload_file: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(content={"error": f"An unexpected error occurred: {str(e)}"}, status_code=500)

@mate_router.post("/chat")
async def chat(chat_request: ChatRequest):
    try:
        if not chat_request.message and not chat_request.file:
            raise HTTPException(status_code=400, detail="Message and file cannot both be empty")

        if chat_request.file and chat_request.file in document_store:
            doc = document_store[chat_request.file]
            if doc["type"] == "text":
                prompt = f"Based on the following document content, answer this question: {chat_request.message}\n\nDocument content: {doc['content']}"
                response = model.generate_content(prompt)
                mode = "Document"
            elif doc["type"] == "image":
                image_parts = [
                    {
                        "mime_type": chat_request.fileType,
                        "data": base64.b64decode(doc['content'])
                    }
                ]
                prompt = f"Analyze this image and answer the following question: {chat_request.message}"
                response = vision_model.generate_content([prompt, image_parts[0]])
                mode = "Vision"
        else:
            response = model.generate_content(chat_request.message)
            mode = "Direct"

        response_text = response.text

        return JSONResponse(content={"response": response_text, "mode": mode})
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(content={"error": f"An unexpected error occurred: {str(e)}"}, status_code=500)

def set_templates(templates):
    global mate_templates
    mate_templates = templates