from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.routes import properties

app = FastAPI(
    title="Frankfurt Property Intelligence API",
    description="Bodenrichtwerte + Lebensqualität-Index für Frankfurt am Main",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(properties.router, prefix="/api")
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
@app.head("/")
def root():
    return FileResponse("frontend/index.html")
