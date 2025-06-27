# codescribe-backend/main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
import json
import os
import asyncio
from datetime import datetime

app = FastAPI(title="CodeScribe AI Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models for communication with IntelliJ plugin
class MethodInfo(BaseModel):
    name: str
    signature: str
    annotations: List[str]
    complexity: int

class FieldInfo(BaseModel):
    name: str
    type: str
    annotations: List[str]

class ClassInfo(BaseModel):
    name: str
    package_name: str
    source_code: str
    annotations: List[str]
    methods: List[MethodInfo]
    fields: List[FieldInfo]

class CodeAnalysisRequest(BaseModel):
    project_name: str
    classes: List[ClassInfo]
    analysis_type: str = "full"

class AIDocumentationResponse(BaseModel):
    documentation: str
    insights: List[str]
    suggestions: List[str]
    architectural_patterns: List[str]

# AI Service for qwen2.5-coder
class CoderAIService:
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        
    async def get_available_model(self) -> Optional[str]:
        """Check if qwen2.5-coder is available"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                if response.status_code == 200:
                    models = [model["name"] for model in response.json().get("models", [])]
                    
                    # Prefer qwen2.5-coder
                    if "qwen2.5-coder:7b-instruct" in models:
                        return "qwen2.5-coder:7b-instruct"
                    
                    # Fallback to any available model
                    return models[0] if models else None
        except:
            pass
        return None
        
    async def analyze_code(self, prompt: str) -> Optional[str]:
        """Analyze code with qwen2.5-coder"""
        model = await self.get_available_model()
        if not model:
            return None
            
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "top_p": 0.9,
                            "num_predict": 800
                        }
                    }
                )
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "")
        except Exception as e:
            print(f"AI analysis error: {e}")
        return None

ai_service = CoderAIService()

@app.get("/")
async def root():
    """Welcome endpoint"""
    return {"message": "CodeScribe AI Backend is running!", "model": "qwen2.5-coder:7b-instruct"}

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    model = await ai_service.get_available_model()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "ollama_available": model is not None,
        "active_model": model,
        "code_optimized": "qwen2.5-coder" in (model or "")
    }

@app.post("/api/v1/analyze-code", response_model=AIDocumentationResponse)
async def analyze_code(request: CodeAnalysisRequest):
    """Main endpoint for AI code analysis"""
    
    print(f"📊 Analyzing project: {request.project_name} ({len(request.classes)} classes)")
    
    # Build analysis prompt
    prompt = create_analysis_prompt(request)
    
    # Get AI analysis
    ai_response = await ai_service.analyze_code(prompt)
    
    if not ai_response:
        return create_fallback_response(request)
    
    return parse_ai_response(ai_response, request)

def create_analysis_prompt(request: CodeAnalysisRequest) -> str:
    """Create optimized prompt for Spring Boot analysis"""
    
    # Analyze Spring components
    controllers = [c for c in request.classes if any('Controller' in ann for ann in c.annotations)]
    services = [c for c in request.classes if any('Service' in ann for ann in c.annotations)]
    repositories = [c for c in request.classes if any('Repository' in ann for ann in c.annotations)]
    
    # Build class summary
    class_summary = []
    for cls in request.classes[:5]:  # Limit to prevent overwhelming
        spring_type = "Component"
        if any('Controller' in ann for ann in cls.annotations):
            spring_type = "REST Controller"
        elif any('Service' in ann for ann in cls.annotations):
            spring_type = "Service"
        elif any('Repository' in ann for ann in cls.annotations):
            spring_type = "Repository"
        
        class_summary.append(f"- {cls.name} ({spring_type}, {len(cls.methods)} methods)")
    
    prompt = f"""Analyze this Spring Boot project "{request.project_name}":

STRUCTURE:
- Controllers: {len(controllers)}
- Services: {len(services)}
- Repositories: {len(repositories)}
- Total Classes: {len(request.classes)}

KEY CLASSES:
{chr(10).join(class_summary)}

Please provide analysis covering:
1. What does this application do?
2. What architectural patterns are used?
3. Code quality assessment
4. Specific improvement recommendations

Be practical and Spring Boot focused."""
    
    return prompt

def parse_ai_response(ai_response: str, request: CodeAnalysisRequest) -> AIDocumentationResponse:
    """Parse AI response into structured format"""
    
    documentation = f"# 🤖 AI Analysis: {request.project_name}\n\n{ai_response}"
    
    # Extract insights and suggestions from response
    lines = ai_response.split('\n')
    insights = []
    suggestions = []
    patterns = []
    
    for line in lines:
        line = line.strip()
        if any(word in line.lower() for word in ['recommend', 'should', 'consider']):
            suggestions.append(line)
        elif any(word in line.lower() for word in ['pattern', 'architecture', 'mvc']):
            patterns.append(line)
        elif any(word in line.lower() for word in ['quality', 'complexity', 'issue']):
            insights.append(line)
    
    # Provide defaults if extraction didn't work well
    if not patterns:
        patterns = ["Spring Boot MVC Architecture"]
    if not suggestions:
        suggestions = ["Add comprehensive API documentation", "Implement proper exception handling"]
    if not insights:
        insights = ["Code follows Spring Boot conventions"]
    
    return AIDocumentationResponse(
        documentation=documentation,
        insights=insights[:3],
        suggestions=suggestions[:3],
        architectural_patterns=patterns[:2]
    )

def create_fallback_response(request: CodeAnalysisRequest) -> AIDocumentationResponse:
    """Fallback when AI is not available"""
    
    controllers = len([c for c in request.classes if any('Controller' in ann for ann in c.annotations)])
    services = len([c for c in request.classes if any('Service' in ann for ann in c.annotations)])
    repositories = len([c for c in request.classes if any('Repository' in ann for ann in c.annotations)])
    
    documentation = f"""# 📊 Analysis: {request.project_name}

## Project Structure
- Controllers: {controllers}
- Services: {services}
- Repositories: {repositories}
- Total Classes: {len(request.classes)}

## Assessment
{"Standard Spring Boot MVC application" if controllers > 0 and services > 0 else "Basic Spring Boot application"}
with {"good separation of concerns" if repositories > 0 else "simple structure"}.

⚠️ AI analysis unavailable - using basic analysis."""
    
    return AIDocumentationResponse(
        documentation=documentation,
        insights=["Basic Spring Boot structure detected"],
        suggestions=["Ensure AI backend is running for detailed analysis"],
        architectural_patterns=["Spring Boot Application"]
    )

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting CodeScribe Backend")
    print("📊 Optimized for: qwen2.5-coder:7b-instruct")
    print("🌐 Server: http://localhost:8000")
    print("📋 Health: http://localhost:8000/api/v1/health")
    uvicorn.run(app, host="0.0.0.0", port=8000)