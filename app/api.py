from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from app.models import CodeAnalysisRequest, AIDocumentationResponse
from app.services import SimpleAIService
from app.utils import parse_structured_response

app = FastAPI(title="CodeScribe AI Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_service = SimpleAIService()

@app.get("/")
async def root():
    return {"message": "CodeScribe Enhanced AI Backend", "status": "running"}

@app.get("/api/v1/health")
async def health_check():
    model = await ai_service.get_available_model()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "ollama_available": model is not None,
        "active_model": model,
        "code_optimized": "qwen2.5-coder" in (model or ""),
        "features": ["structured_prompts", "section_parsing", "enhanced_analysis"]
    }

@app.post("/api/v1/analyze-code", response_model=AIDocumentationResponse)
async def analyze_code(request: CodeAnalysisRequest):
    print(f"\n🎯 NEW ENHANCED REQUEST: {request.project_name}")
    print(f"📊 Classes to analyze: {len(request.classes)}")

    ai_response = await ai_service.analyze_code(request)
    
    if ai_response:
        print("✅ AI SUCCESS! Parsing structured response...")
        return parse_structured_response(ai_response, request)
    else:
        print("❌ AI FAILED - using enhanced fallback")

        controllers = len([c for c in request.classes if any('Controller' in ann for ann in c.annotations)])
        services = len([c for c in request.classes if any('Service' in ann for ann in c.annotations)])
        repositories = len([c for c in request.classes if 
                           any('Repository' in ann for ann in c.annotations) or
                           c.name.endswith('Repository') or
                           any('JpaRepository' in ann or 'CrudRepository' in ann for ann in c.annotations)])
        entities = len([c for c in request.classes if any('Entity' in ann for ann in c.annotations)])

        fallback_doc = f"""# 📊 {request.project_name} - Static Analysis

## 📋 Project Overview
Spring Boot application with {len(request.classes)} classes organized in a layered architecture.

## 🏗️ Architecture Analysis
Standard Spring Boot MVC pattern with clear separation between web, business, and data layers.

**Component Distribution:**
- Controllers: {controllers}
- Services: {services}
- Repositories: {repositories}
- Entities: {entities}
- Total Classes: {len(request.classes)}

⚠️ *AI analysis unavailable - using static analysis*"""

        return AIDocumentationResponse(
            documentation=fallback_doc,
            insights=[
                f"Well-structured Spring Boot application with {len(request.classes)} classes",
                f"Good separation of concerns with {controllers} controllers and {services} services",
                "Standard layered architecture pattern detected"
            ],
            suggestions=[
                "Check AI backend connectivity for enhanced analysis",
                "Consider adding integration tests",
                "Implement proper error handling"
            ],
            architectural_patterns=["Spring Boot MVC", "Layered Architecture"]
        )
