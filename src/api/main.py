# FastAPI entry point
import json
import os
import mimetypes
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Register JS and JSX MIME types explicitly to fix Windows registry overrides
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".jsx")

app = FastAPI(title="AI Ocean Platform API")

# Configure CORS for local development (Vite runs on port 5173 by default)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/data")
def get_dashboard_data():
    """
    Serve the AI-generated JSON data over a REST endpoint.
    This replaces the old method of writing directly to a Javascript file.
    """
    # The pipeline script writes to data/processed/dashboard_data.json
    data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "processed", "dashboard_data.json")
    
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(
            content=data,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )
    else:
        # Fallback if pipeline hasn't run yet
        return JSONResponse(content={"error": "Data not found. Please run the pipeline exporter first."}, status_code=404)

# Mount the static frontend directory so it runs on the same port as the API
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
frontend_dist_path = os.path.join(root_dir, "frontend", "dist")
frontend_src_path = os.path.join(root_dir, "frontend")

@app.get("/data.js")
def get_data_js():
    js_path = os.path.join(root_dir, "frontend", "data.js")
    if os.path.exists(js_path):
        from fastapi.responses import FileResponse
        return FileResponse(js_path, media_type="application/javascript")
    return JSONResponse(content={"error": "Not found"}, status_code=404)

if os.path.exists(frontend_dist_path):
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="frontend")
elif os.path.exists(frontend_src_path):
    app.mount("/", StaticFiles(directory=frontend_src_path, html=True), name="frontend")

