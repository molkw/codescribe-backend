# codescribe-backend/main.py
# Simple version that should definitely work

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

# Data models
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

# Simple AI Service - minimal configuration for maximum compatibility
class SimpleAIService:
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        
    async def get_available_model(self) -> Optional[str]:
        try:
            print("🔍 Checking models...")
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                if response.status_code == 200:
                    models = [model["name"] for model in response.json().get("models", [])]
                    print(f"📋 Available: {models}")
                    
                    if "qwen2.5-coder:7b-instruct" in models:
                        print("✅ Using qwen2.5-coder:7b-instruct")
                        return "qwen2.5-coder:7b-instruct"
                    return models[0] if models else None
        except Exception as e:
            print(f"❌ Model check failed: {e}")
        return None
        
    async def analyze_code(self, prompt: str) -> Optional[str]:
        model = await self.get_available_model()
        if not model:
            print("❌ No model available")
            return None
            
        print(f"🚀 Analyzing with {model}...")
        print(f"📝 Prompt: {prompt[:100]}...")
        
        try:
            # VERY simple request - minimal options
            request_data = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 150  # Very short response
                }
            }
            
            print("📡 Sending to Ollama...")
            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minute timeout
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json=request_data
                )
                
                print(f"📊 Status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    ai_response = result.get("response", "").strip()
                    print(f"✅ Got response: {len(ai_response)} chars")
                    print(f"📄 Preview: {ai_response[:100]}...")
                    
                    if ai_response:
                        return ai_response
                    else:
                        print("❌ Empty response")
                        return None
                else:
                    print(f"❌ HTTP {response.status_code}: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

ai_service = SimpleAIService()

@app.get("/")
async def root():
    return {"message": "CodeScribe Simple AI Backend", "status": "running"}

@app.get("/api/v1/health")
async def health_check():
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
    print(f"\n🎯 NEW REQUEST: {request.project_name}")
    
    # Simple prompt
    controllers = len([c for c in request.classes if any('Controller' in ann for ann in c.annotations)])
    services = len([c for c in request.classes if any('Service' in ann for ann in c.annotations)])
    repositories = len([c for c in request.classes if any('Repository' in ann for ann in c.annotations)])
    
    prompt = f"""Spring Boot project analysis:
Project: {request.project_name}
Classes: {len(request.classes)} total ({controllers} controllers, {services} services, {repositories} repositories)

Give me:
1. What this app does (one sentence)
2. Architecture pattern 
3. One improvement suggestion

Keep it very short."""

    print(f"📝 Prompt ready ({len(prompt)} chars)")
    
    # Try AI analysis
    ai_response = await ai_service.analyze_code(prompt)
    
    if ai_response:
        print("✅ AI SUCCESS!")
        documentation = f"# 🤖 {request.project_name}\n\n{ai_response}"
        
        # Simple parsing
        lines = [l.strip() for l in ai_response.split('\n') if l.strip()]
        
        return AIDocumentationResponse(
            documentation=documentation,
            insights=[lines[0] if lines else "AI analysis completed"],
            suggestions=[lines[-1] if len(lines) > 1 else "Consider adding more layers"],
            architectural_patterns=["Spring Boot MVC" if controllers > 0 else "Spring Boot"]
        )
    else:
        print("❌ AI FAILED - using fallback")
        return AIDocumentationResponse(
            documentation=f"# 📊 {request.project_name}\n\nBasic analysis: {controllers} controllers, {services} services, {repositories} repositories.\n\n⚠️ AI analysis failed.",
            insights=["Basic Spring Boot structure"],
            suggestions=["Check AI backend logs"],
            architectural_patterns=["Spring Boot"]
        )

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Simple CodeScribe Backend")
    print("🔧 Minimal configuration for maximum compatibility")
    uvicorn.run(app, host="0.0.0.0", port=8000)
    