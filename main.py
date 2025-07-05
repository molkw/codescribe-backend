# codescribe-backend/main.py
# Debug version to see what's happening with AI calls

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

# Enhanced AI Service with debugging
class CoderAIService:
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        
    async def get_available_model(self) -> Optional[str]:
        """Check if qwen2.5-coder is available"""
        try:
            print("🔍 DEBUG: Checking available models...")
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                if response.status_code == 200:
                    models_data = response.json()
                    models = [model["name"] for model in models_data.get("models", [])]
                    print(f"🔍 DEBUG: Available models: {models}")
                    
                    # Prefer qwen2.5-coder
                    if "qwen2.5-coder:7b-instruct" in models:
                        print("✅ DEBUG: Found qwen2.5-coder:7b-instruct")
                        return "qwen2.5-coder:7b-instruct"
                    
                    # Fallback to any available model
                    if models:
                        print(f"⚠️ DEBUG: Using fallback model: {models[0]}")
                        return models[0]
                    else:
                        print("❌ DEBUG: No models found")
                        return None
                else:
                    print(f"❌ DEBUG: Ollama API returned status {response.status_code}")
                    return None
        except Exception as e:
            print(f"❌ DEBUG: Exception checking models: {e}")
            return None
        
    async def analyze_code(self, prompt: str) -> Optional[str]:
        """Analyze code with qwen2.5-coder"""
        print("🔍 DEBUG: Starting AI analysis...")
        
        model = await self.get_available_model()
        if not model:
            print("❌ DEBUG: No model available for analysis")
            return None
            
        print(f"🔍 DEBUG: Using model: {model}")
        print(f"🔍 DEBUG: Prompt length: {len(prompt)} characters")
        print(f"🔍 DEBUG: Prompt preview: {prompt[:200]}...")
        
        try:
            request_data = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 800
                }
            }
            
            print(f"🔍 DEBUG: Sending request to {self.ollama_url}/api/generate")
            print(f"🔍 DEBUG: Request data: {json.dumps(request_data, indent=2)}")
            
            async with httpx.AsyncClient(timeout=180.0) as client:  # Increased from 90 to 180 seconds
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json=request_data
                )
                
                print(f"🔍 DEBUG: Response status: {response.status_code}")
                print(f"🔍 DEBUG: Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"🔍 DEBUG: Response JSON keys: {list(result.keys())}")
                    
                    ai_response = result.get("response", "")
                    print(f"🔍 DEBUG: AI response length: {len(ai_response)} characters")
                    print(f"🔍 DEBUG: AI response preview: {ai_response[:300]}...")
                    
                    if ai_response:
                        print("✅ DEBUG: AI analysis successful!")
                        return ai_response
                    else:
                        print("❌ DEBUG: AI response is empty")
                        return None
                else:
                    response_text = response.text
                    print(f"❌ DEBUG: HTTP error {response.status_code}")
                    print(f"❌ DEBUG: Response body: {response_text}")
                    return None
                    
        except httpx.TimeoutException as e:
            print(f"⏰ DEBUG: Timeout error: {e}")
            return None
        except Exception as e:
            print(f"❌ DEBUG: Exception during AI analysis: {e}")
            print(f"❌ DEBUG: Exception type: {type(e).__name__}")
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
    
    print(f"📊 DEBUG: Analyzing project: {request.project_name} ({len(request.classes)} classes)")
    
    # Build analysis prompt
    prompt = create_analysis_prompt(request)
    print(f"📊 DEBUG: Generated prompt for AI analysis")
    
    # Get AI analysis
    print("📊 DEBUG: Calling AI service...")
    ai_response = await ai_service.analyze_code(prompt)
    
    if not ai_response:
        print("📊 DEBUG: AI analysis failed, using fallback")
        return create_fallback_response(request)
    
    print("📊 DEBUG: AI analysis succeeded, parsing response")
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
    
    print(f"🔍 DEBUG: Created prompt with {len(prompt)} characters")
    return prompt

def parse_ai_response(ai_response: str, request: CodeAnalysisRequest) -> AIDocumentationResponse:
    """Parse AI response into structured format"""
    
    print(f"🔍 DEBUG: Parsing AI response with {len(ai_response)} characters")
    
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
    
    print(f"🔍 DEBUG: Extracted {len(insights)} insights, {len(suggestions)} suggestions, {len(patterns)} patterns")
    
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
    print("🚀 Starting CodeScribe Backend (DEBUG MODE)")
    print("📊 Optimized for: qwen2.5-coder:7b-instruct")
    print("🌐 Server: http://localhost:8000")
    print("📋 Health: http://localhost:8000/api/v1/health")
    print("🔬 Analysis: http://localhost:8000/api/v1/analyze-code")
    print("🔍 Debug logs will show all AI communication details")
    uvicorn.run(app, host="0.0.0.0", port=8000)