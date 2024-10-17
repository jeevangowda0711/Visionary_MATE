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
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables and set up API key
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is not set in the environment variables.")

genai.configure(api_key=GOOGLE_API_KEY)

# Initialize models
gemini_flash = genai.GenerativeModel('models/gemini-1.5-flash')
embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
llm = Gemini(model_name="models/gemini-1.5-flash", api_key=GOOGLE_API_KEY)
Settings.embed_model = embed_model
Settings.llm = llm

# Initialize the APIRouter
mate_router = APIRouter()
mate_templates = None

# Global index variable
index = None

class ChatRequest(BaseModel):
    message: str = Field(default="")
    file: str | None = Field(default=None)
    fileType: str | None = Field(default=None)

@mate_router.get("/", response_class=HTMLResponse)
async def mate_home(request: Request):
    return mate_templates.TemplateResponse("mate.html", {"request": request})

def detect_file_type(filename):
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"

@mate_router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    global index
    try:
        content = await file.read()
        file_type = detect_file_type(file.filename)
        logger.info(f"Uploading file: {file.filename} (Type: {file_type})")

        if file_type.startswith(("image/", "audio/", "video/")):
            encoded_file = base64.b64encode(content).decode()
            logger.info(f"Media file processed successfully: {file.filename}")
            return JSONResponse(content={
                "message": f"{file_type} uploaded successfully",
                "filename": file.filename,
                "file_data": encoded_file,
                "mime_type": file_type
            })

        # Use SimpleDirectoryReader to process document files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = os.path.join(temp_dir, file.filename)
            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(content)
            
            logger.info(f"Attempting to process file: {file.filename}")
            reader = SimpleDirectoryReader(temp_dir)
            documents = reader.load_data()
            logger.info(f"Successfully processed file: {file.filename}")

        if not documents:
            logger.warning(f"No content extracted from file: {file.filename}")
            raise ValueError("No content could be extracted from the file.")

        index = VectorStoreIndex.from_documents(documents)
        logger.info(f"File processed and indexed successfully: {file.filename}")
        logger.info(f"Index now contains {len(index.docstore.docs)} documents")

        return JSONResponse(content={
            "message": f"{file_type} file processed and indexed successfully",
            "filename": file.filename,
            "content_preview": documents[0].text[:500] + "..." if len(documents[0].text) > 500 else documents[0].text
        })
    except Exception as e:
        logger.error(f"Error in upload_file: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(content={"error": f"An unexpected error occurred: {str(e)}"}, status_code=500)

@mate_router.post("/chat")
async def chat(chat_request: ChatRequest):
    global index
    try:
        if not chat_request.message and not chat_request.file:
            raise HTTPException(status_code=400, detail="Message and file cannot both be empty")

        if chat_request.file:
            if chat_request.fileType.startswith(('image/', 'audio/', 'video/')):
                # Handle media files directly with Gemini
                prompt = [chat_request.message or f"Analyze this {chat_request.fileType.split('/')[0]}", 
                          {"mime_type": chat_request.fileType, "data": base64.b64decode(chat_request.file)}]
                response = gemini_flash.generate_content(prompt)
                mode = chat_request.fileType.split('/')[0].capitalize()
            else:
                # For document types, use the RAG pipeline
                if index:
                    query_engine = index.as_query_engine()
                    response = query_engine.query(chat_request.message)
                    mode = "RAG"
                else:
                    raise HTTPException(status_code=400, detail="No indexed documents available for query")
        elif chat_request.message:
            if index:
                # If there are indexed documents, use RAG pipeline
                query_engine = index.as_query_engine()
                response = query_engine.query(chat_request.message)
                mode = "RAG"
            else:
                # If no documents are indexed, use direct Gemini processing
                response = gemini_flash.generate_content(chat_request.message)
                mode = "Direct"

        # Extract the text content from the response
        if isinstance(response, str):
            response_text = response
        else:
            response_text = response.text if hasattr(response, 'text') else str(response)

        return JSONResponse(content={"response": response_text, "mode": mode})
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(content={"error": f"An unexpected error occurred: {str(e)}"}, status_code=500)

def set_templates(templates):
    global mate_templates
    mate_templates = templates