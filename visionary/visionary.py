from fastapi import FastAPI, Request, File, UploadFile, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware  # Added for CORS
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import google.generativeai as genai
from google.cloud import texttospeech_v1 as texttospeech
from google.oauth2 import service_account
from dotenv import load_dotenv
import os
import base64
from collections import deque
import re
import requests

# Load environment variables
load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust according to your security needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for Visionary system
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates for Visionary
visionary_templates = Jinja2Templates(directory="visionary/templates")

# Function to dynamically set templates
def set_templates(templates):
    global visionary_templates
    visionary_templates = templates

# Setup API router for Visionary system
visionary_router = APIRouter()


# Configure Gemini API
genai_api_key = os.getenv("GEMINI_API_KEY")
if not genai_api_key:
    print("Warning: GEMINI_API_KEY is not set in the environment variables")
else:
    genai.configure(api_key=genai_api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

# Configure Text-to-Speech client
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if not credentials_path:
    print("Warning: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set")
else:
    credentials = service_account.Credentials.from_service_account_file(str(credentials_path))
    tts_client = texttospeech.TextToSpeechClient(credentials=credentials)

# Mapbox API key
mapbox_api_key = os.getenv("MAPBOX_API_KEY")
if not mapbox_api_key:
    print("Warning: MAPBOX_API_KEY is not set in the environment variables")

# Google Places API key
google_places_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
if not google_places_api_key:
    print("Warning: GOOGLE_PLACES_API_KEY is not set in the environment variables")

DEFAULT_PROMPT = """
Please respond to my audio questions by only following these specific rules:

1. If I ask questions like "What is in front of me?", "Can I cross the road?", or "What is this object?", provide a concise description of the given image in the same language as the question, considering safety concerns for blind users.

2. For directional or location-based queries, like "How do I get to the nearest Walmart?", respond with: "Opening directions for {location}" in English, regardless of the language used.

3. For recent information queries like “What’s happening in the world?”, respond with: "Searching..." and repeat the question in the same language.

4. For general queries, respond in the same language as the question.

5. End each response by specifying the language used.
"""

@visionary_router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    # Pass the API key to the template for frontend use
    return visionary_templates.TemplateResponse("visionary.html", {
        "request": request,
        "mapbox_api_key": mapbox_api_key
    })

@visionary_router.post("/process_audio_and_image")
async def process_audio_and_image(audio: UploadFile = File(...), image: UploadFile = File(...)):
    try:
        # Process audio and image
        audio_content = await audio.read()
        image_content = await image.read()
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        image_base64 = base64.b64encode(image_content).decode('utf-8')

        # Send both audio and image to Gemini
        response = model.generate_content([
            DEFAULT_PROMPT,
            "Process this audio input and image:",
            {"mime_type": audio.content_type, "data": audio_base64},
            {"mime_type": image.content_type, "data": image_base64}
        ])

        text_response = response.text if response.text else "I'm sorry, I couldn't process the input."
        print(f"Gemini response: {text_response}")

        if not text_response or not isinstance(text_response, str):
            raise ValueError("Invalid text response received from the Gemini API")

        # Check if the response indicates navigation
        is_navigation = text_response.lower().startswith("opening directions for")
        location = None
        if is_navigation:
            # Use regular expressions for case-insensitive matching
            match = re.match(r"opening directions for\s*(.+?)[\.\n]", text_response, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
            else:
                # Fallback: Extract text after the phrase
                index = text_response.lower().index("opening directions for") + len("opening directions for")
                location_text = text_response[index:].strip()
                # Split at the first period or newline
                location = re.split(r'[\.\n]', location_text, 1)[0].strip()
            print(f"Extracted location: {location}")

        # Extract language from the response
        text_response_clean = text_response.strip()

        # Remove trailing periods or newlines
        while text_response_clean and text_response_clean[-1] in '.\n':
            text_response_clean = text_response_clean[:-1].strip()

        # Assume the language is the last word after the last period
        if '.' in text_response_clean:
            content, lang = text_response_clean.rsplit('.', 1)
        else:
            content = text_response_clean
            lang = 'english'

        lang = lang.strip().lower()

        language_mappings = {
            'english': 'english',
            'spanish': 'spanish',
            # Add other languages as needed
        }

        language = language_mappings.get(lang, 'english')

        print(f"Extracted language: {language}")

        # Synthesizing audio response based on content and language
        audio_content = synthesize_speech(content.strip(), language)

        if not audio_content:
            raise ValueError("Invalid audio content generated")

        return JSONResponse(content={
            "response": text_response,
            "audio": audio_content,
            "is_navigation": is_navigation,
            "location": location
        })
    except Exception as e:
        print(f"Error generating audio: {str(e)}")
        error_message = "Sorry, there was an error processing your request."
        return JSONResponse(content={"error": error_message}, status_code=500)

@visionary_router.post("/synthesize_speech")
async def synthesize_speech_endpoint(request: Request):
    data = await request.json()
    text = data.get('text', '')
    language = data.get('language', 'english')
    audio_content = synthesize_speech(text, language)
    if audio_content:
        return JSONResponse(content={"audio": audio_content})
    else:
        return JSONResponse(content={"error": "Failed to synthesize speech"}, status_code=500)

from pydantic import BaseModel

class NearestPlaceRequest(BaseModel):
    keyword: str
    latitude: float
    longitude: float

@visionary_router.post("/get_nearest_place")
async def get_nearest_place(request_data: NearestPlaceRequest):
    keyword = request_data.keyword
    latitude = request_data.latitude
    longitude = request_data.longitude

    if not google_places_api_key:
        return JSONResponse(content={"error": "Server configuration error: Google Places API key not set"}, status_code=500)

    try:
        # Use Google Places API Nearby Search
        places_url = (
            f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            f"?location={latitude},{longitude}"
            f"&rankby=distance"
            f"&keyword={requests.utils.quote(keyword)}"
            f"&key={google_places_api_key}"
        )

        response = requests.get(places_url)
        data = response.json()

        if data.get('results'):
            place = data['results'][0]
            dest_latitude = place['geometry']['location']['lat']
            dest_longitude = place['geometry']['location']['lng']
            return {"latitude": dest_latitude, "longitude": dest_longitude}
        else:
            # If no nearby places found, use Geocoding API
            geocode_url = (
                f"https://maps.googleapis.com/maps/api/geocode/json"
                f"?address={requests.utils.quote(keyword)}"
                f"&key={google_places_api_key}"
            )
            geocode_response = requests.get(geocode_url)
            geocode_data = geocode_response.json()

            if geocode_data.get('results'):
                location = geocode_data['results'][0]['geometry']['location']
                dest_latitude = location['lat']
                dest_longitude = location['lng']
                return {"latitude": dest_latitude, "longitude": dest_longitude}
            else:
                return JSONResponse(content={"error": "Location not found"}, status_code=404)
    except Exception as e:
        print(f"Error fetching location: {e}")
        return JSONResponse(content={"error": "Error fetching location"}, status_code=500)

def synthesize_speech(text, language="english"):
    if not isinstance(text, str) or not text.strip():
        print("Error: The text input for speech synthesis is invalid or empty.")
        return None

    input_text = texttospeech.SynthesisInput(text=text)

    # Map of language codes to appropriate Wavenet voices
    language_voices = {
        'english': ('en-US', ['en-US-Wavenet-D', 'en-US-Wavenet-A', 'en-US-Wavenet-B', 'en-US-Wavenet-C']),
        'hindi': ('hi-IN', ['hi-IN-Wavenet-D', 'hi-IN-Wavenet-A', 'hi-IN-Wavenet-B', 'hi-IN-Wavenet-C']),
        'spanish': ('es-ES', ['es-ES-Wavenet-B', 'es-ES-Wavenet-A', 'es-ES-Wavenet-C', 'es-ES-Wavenet-D']),
        'french': ('fr-FR', ['fr-FR-Wavenet-C', 'fr-FR-Wavenet-A', 'fr-FR-Wavenet-B', 'fr-FR-Wavenet-D']),
        'german': ('de-DE', ['de-DE-Wavenet-F', 'de-DE-Wavenet-A', 'de-DE-Wavenet-B', 'de-DE-Wavenet-C']),
        'kannada': ('kn-IN', ['kn-IN-Wavenet-A']),
        'telugu': ('te-IN', ['te-IN-Wavenet-B', 'te-IN-Wavenet-A']),
        'tamil': ('ta-IN', ['ta-IN-Wavenet-D', 'ta-IN-Wavenet-A', 'ta-IN-Wavenet-B', 'ta-IN-Wavenet-C']),
        'malayalam': ('ml-IN', ['ml-IN-Wavenet-D', 'ml-IN-Wavenet-A', 'ml-IN-Wavenet-B', 'ml-IN-Wavenet-C']),
        'bengali': ('bn-IN', ['bn-IN-Wavenet-A']),
        'gujarati': ('gu-IN', ['gu-IN-Wavenet-A']),
        'marathi': ('mr-IN', ['mr-IN-Wavenet-A']),
        'japanese': ('ja-JP', ['ja-JP-Wavenet-D', 'ja-JP-Wavenet-A', 'ja-JP-Wavenet-B', 'ja-JP-Wavenet-C']),
        'korean': ('ko-KR', ['ko-KR-Wavenet-D', 'ko-KR-Wavenet-A', 'ko-KR-Wavenet-B', 'ko-KR-Wavenet-C']),
        'chinese': ('cmn-CN', ['cmn-CN-Wavenet-D', 'cmn-CN-Wavenet-A', 'cmn-CN-Wavenet-B', 'cmn-CN-Wavenet-C']),
        'arabic': ('ar-XA', ['ar-XA-Wavenet-B', 'ar-XA-Wavenet-A', 'ar-XA-Wavenet-C', 'ar-XA-Wavenet-D']),
        'russian': ('ru-RU', ['ru-RU-Wavenet-D', 'ru-RU-Wavenet-A', 'ru-RU-Wavenet-B', 'ru-RU-Wavenet-C']),
        'portuguese': ('pt-BR', ['pt-BR-Wavenet-B', 'pt-BR-Wavenet-A', 'pt-BR-Wavenet-C', 'pt-BR-Wavenet-D']),
        'italian': ('it-IT', ['it-IT-Wavenet-D', 'it-IT-Wavenet-A', 'it-IT-Wavenet-B', 'it-IT-Wavenet-C']),
        'dutch': ('nl-NL', ['nl-NL-Wavenet-E', 'nl-NL-Wavenet-A', 'nl-NL-Wavenet-B', 'nl-NL-Wavenet-C']),
        'polish': ('pl-PL', ['pl-PL-Wavenet-E', 'pl-PL-Wavenet-A', 'pl-PL-Wavenet-B', 'pl-PL-Wavenet-C']),
        'swedish': ('sv-SE', ['sv-SE-Wavenet-A', 'sv-SE-Wavenet-B', 'sv-SE-Wavenet-C']),
        'turkish': ('tr-TR', ['tr-TR-Wavenet-E', 'tr-TR-Wavenet-A', 'tr-TR-Wavenet-B', 'tr-TR-Wavenet-C']),
        'vietnamese': ('vi-VN', ['vi-VN-Wavenet-D', 'vi-VN-Wavenet-A', 'vi-VN-Wavenet-B', 'vi-VN-Wavenet-C']),
        'indonesian': ('id-ID', ['id-ID-Wavenet-D', 'id-ID-Wavenet-A', 'id-ID-Wavenet-B', 'id-ID-Wavenet-C']),
        'thai': ('th-TH', ['th-TH-Wavenet-C', 'th-TH-Wavenet-A', 'th-TH-Wavenet-B']),
        'punjabi': ('pa-IN', ['pa-IN-Wavenet-A', 'pa-IN-Wavenet-B', 'pa-IN-Wavenet-C', 'pa-IN-Wavenet-D']),
    }
    language_code, voice_names = language_voices.get(language.lower(), ('en-US', ['en-US-Wavenet-D']))
    voice_name = voice_names[0]  # Pick the first voice from the list

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=voice_name
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    try:
        response = tts_client.synthesize_speech(
            input=input_text, voice=voice, audio_config=audio_config
        )
        audio_base64 = base64.b64encode(response.audio_content).decode('utf-8')
        return f"data:audio/mp3;base64,{audio_base64}"
    except Exception as e:
        print(f"Error during speech synthesis: {str(e)}")
        return None

# Print registered routes
print("Registered Routes:")
for route in app.router.routes:
    print(f"{route.path} -> {route.name}")

# Add the router for Visionary
app.include_router(visionary_router, prefix="/visionary")

# Start the FastAPI application
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)