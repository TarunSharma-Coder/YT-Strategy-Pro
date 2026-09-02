import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import analysis, thumbnails, comments, settings

app = FastAPI(
    title="YouTube Strategy & Packaging Intelligence API",
    description="High-performance backend API powering the YouTube Strategy & Outlier Dashboard",
    version="2.0.0",
)

# Enable CORS for React/Next.js frontend development and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(analysis.router)
app.include_router(thumbnails.router)
app.include_router(comments.router)
app.include_router(settings.router)

@app.get("/")
def root():
    return {
        "message": "YouTube Strategy & Packaging Intelligence API is running",
        "docs": "/docs",
        "health": "/api/health",
        "version": "2.0.0",
    }

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "youtube-strategy-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
