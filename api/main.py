"""
FastAPI application for TradePulse IQ Dashboard
Provides REST API endpoints for the trading platform
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os
import logging

# Import API routers
from api.auth import router as auth_router
from api.portfolio import router as portfolio_router
from api.trades import router as trades_router
from api.strategies_api import router as strategies_router
from api.training import router as training_router
from api.training_v2 import router as training_v2_router  # V2 Training System
from api.training_configurations import router as training_configs_router
from api.exchanges import router as exchanges_router
from api.analytics import router as analytics_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="TradePulse IQ API",
    description="Trading Platform API for dashboard and analytics",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "TradePulse IQ API"}

# Include API routers
app.include_router(auth_router, tags=["Authentication"])
app.include_router(portfolio_router, tags=["Portfolio"])
app.include_router(trades_router, tags=["Trades"])
app.include_router(strategies_router, tags=["Strategies"])
app.include_router(training_router, tags=["Training"])
app.include_router(training_v2_router, tags=["Training V2"])  # V2 Training System
app.include_router(training_configs_router, tags=["Training Configurations"])
app.include_router(exchanges_router, tags=["Exchanges"])
app.include_router(analytics_router, tags=["Analytics"])

# API test page for debugging
@app.get("/test")
async def serve_test_page():
    return FileResponse("api-test.html")

# Serve React app at root
@app.get("/")
async def serve_react_app():
    return FileResponse("api/static/index.html")

# Mount static files for React app assets  
app.mount("/assets", StaticFiles(directory="api/static/assets"), name="assets")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)