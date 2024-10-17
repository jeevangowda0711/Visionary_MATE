import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routers
from multimodal_mate.mate import mate_router, set_templates as set_mate_templates
from visionary.visionary import visionary_router, set_templates as set_visionary_templates

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/mate/static", StaticFiles(directory="multimodal_mate/static"), name="mate_static")
app.mount("/visionary/static", StaticFiles(directory="visionary/static"), name="visionary_static")

# Templates directory for the main app
main_templates = Jinja2Templates(directory="templates")

# Create separate template instances for mate and visionary
mate_templates = Jinja2Templates(directory="multimodal_mate/templates")
mate_templates.env.loader.searchpath.append("templates")  # Add root templates directory

visionary_templates = Jinja2Templates(directory="visionary/templates")
visionary_templates.env.loader.searchpath.append("templates")  # Add root templates directory

# Set the templates for both routers
set_mate_templates(mate_templates)
set_visionary_templates(visionary_templates)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Homepage route
@app.get("/", response_class=HTMLResponse)
async def read_home(request: Request):
    return main_templates.TemplateResponse("index.html", {"request": request})

# Include routers
app.include_router(mate_router, prefix="/mate")
app.include_router(visionary_router, prefix="/visionary")

# Add these functions to generate URLs for static files
@app.get("/static/{path:path}")
async def static_files(path: str):
    return FileResponse(f"static/{path}")

@app.get("/mate/static/{path:path}")
async def mate_static_files(path: str):
    return FileResponse(f"multimodal_mate/static/{path}")

@app.get("/visionary/static/{path:path}")
async def visionary_static_files(path: str):
    return FileResponse(f"visionary/static/{path}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)