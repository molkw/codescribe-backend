# codescribe-backend/main.py
# Updated version with improved AI prompt structure

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

# Enhanced AI Service with better prompts
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

    def create_structured_prompt(self, request: CodeAnalysisRequest) -> str:
        """Create a structured prompt for better AI responses"""
        
        # Analyze project composition
        controllers = [c for c in request.classes if any('Controller' in ann for ann in c.annotations)]
        services = [c for c in request.classes if any('Service' in ann for ann in c.annotations)]
        
        # Enhanced repository detection
        repositories = [c for c in request.classes if 
                       any('Repository' in ann for ann in c.annotations) or
                       c.name.endswith('Repository') or
                       any('JpaRepository' in ann or 'CrudRepository' in ann for ann in c.annotations)]
        
        entities = [c for c in request.classes if any('Entity' in ann for ann in c.annotations)]
        
        # Get sample class names for context
        controller_names = [c.name for c in controllers[:3]]
        service_names = [c.name for c in services[:3]]
        entity_names = [c.name for c in entities[:3]]
        
        prompt = f"""Analyze this Spring Boot project: {request.project_name}

PROJECT STRUCTURE:
- {len(controllers)} Controllers: {', '.join(controller_names[:3])}{'...' if len(controllers) > 3 else ''}
- {len(services)} Services: {', '.join(service_names[:3])}{'...' if len(services) > 3 else ''}
- {len(repositories)} Repositories: {len(repositories)} data access classes
- {len(entities)} Entities: {', '.join(entity_names[:3])}{'...' if len(entities) > 3 else ''}
- {len(request.classes)} Total Classes

Provide analysis in EXACTLY this format:

OVERVIEW:
[2-3 sentences about what this application does based on class names and structure]

ARCHITECTURE:
[1-2 sentences about the architectural pattern used - MVC, layered, etc.]

KEY_INSIGHTS:
[2-3 bullet points about interesting technical aspects]

SUGGESTIONS:
[2-3 practical improvement recommendations]

PATTERNS:
[List 2-3 design patterns you can identify from the structure]

Keep each section concise and focused. Base analysis on Spring Boot conventions and class naming patterns."""

        return prompt
        
    async def analyze_code(self, request: CodeAnalysisRequest) -> Optional[str]:
        model = await self.get_available_model()
        if not model:
            print("❌ No model available")
            return None
            
        # Create structured prompt
        prompt = self.create_structured_prompt(request)
        print(f"🚀 Analyzing with {model}...")
        print(f"📝 Prompt length: {len(prompt)} chars")
        
        try:
            request_data = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 300,  # Longer response for structured output
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            }
            
            print("📡 Sending structured prompt to Ollama...")
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json=request_data
                )
                
                print(f"📊 Status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    ai_response = result.get("response", "").strip()
                    print(f"✅ Got response: {len(ai_response)} chars")
                    print(f"📄 Preview: {ai_response[:150]}...")
                    
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

def parse_structured_response(ai_response: str, request: CodeAnalysisRequest) -> AIDocumentationResponse:
    """Parse the structured AI response into proper sections"""
    
    # Enhanced component detection - consistent logic
    controllers = len([c for c in request.classes if any('Controller' in ann for ann in c.annotations)])
    services = len([c for c in request.classes if any('Service' in ann for ann in c.annotations)])
    
    # Enhanced repository detection - SAME logic everywhere
    repositories = len([c for c in request.classes if 
                       any('Repository' in ann for ann in c.annotations) or
                       c.name.endswith('Repository') or
                       any('JpaRepository' in ann or 'CrudRepository' in ann for ann in c.annotations)])
                       
    entities = len([c for c in request.classes if any('Entity' in ann for ann in c.annotations)])
    
    # Initialize sections
    sections = {
        'overview': '',
        'architecture': '',
        'key_insights': [],
        'suggestions': [],
        'patterns': []
    }
    
    lines = ai_response.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detect section headers
        if line.startswith('OVERVIEW:'):
            current_section = 'overview'
            continue
        elif line.startswith('ARCHITECTURE:'):
            current_section = 'architecture'
            continue
        elif line.startswith('KEY_INSIGHTS:'):
            current_section = 'key_insights'
            continue
        elif line.startswith('SUGGESTIONS:'):
            current_section = 'suggestions'
            continue
        elif line.startswith('PATTERNS:'):
            current_section = 'patterns'
            continue
        
        # Add content to appropriate section
        if current_section == 'overview':
            sections['overview'] += line + ' '
        elif current_section == 'architecture':
            sections['architecture'] += line + ' '
        elif current_section in ['key_insights', 'suggestions', 'patterns']:
            if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                sections[current_section].append(line.lstrip('-•* '))
            elif line and not line.isupper():  # Not a section header
                sections[current_section].append(line)
    
    # Build structured documentation with CORRECT counts
    documentation = f"""# 🤖 {request.project_name} - AI Analysis

## 📋 Project Overview
{sections['overview'].strip()}

## 🏗️ Architecture Analysis  
{sections['architecture'].strip()}

**Component Distribution:**
- Controllers: {controllers}
- Services: {services}
- Repositories: {repositories}
- Entities: {entities}
- Total Classes: {len(request.classes)}"""

    # Determine architectural patterns with CORRECT repository count
    architectural_patterns = []
    if controllers > 0 and services > 0:
        architectural_patterns.append("Spring Boot MVC")
    if services > 0 and repositories > 0:
        architectural_patterns.append("Layered Architecture")
    if repositories > 0:
        architectural_patterns.append("Repository Pattern")
    
    # Add detected patterns from AI
    architectural_patterns.extend(sections['patterns'])
    
    return AIDocumentationResponse(
        documentation=documentation,
        insights=sections['key_insights'] if sections['key_insights'] else ["AI analysis completed successfully"],
        suggestions=sections['suggestions'] if sections['suggestions'] else ["Consider adding integration tests"],
        architectural_patterns=list(set(architectural_patterns))  # Remove duplicates
    )

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
    
    # Try AI analysis with structured prompt
    ai_response = await ai_service.analyze_code(request)
    
    if ai_response:
        print("✅ AI SUCCESS! Parsing structured response...")
        return parse_structured_response(ai_response, request)
    else:
        print("❌ AI FAILED - using enhanced fallback")
        
        # Enhanced fallback with better structure
        controllers = len([c for c in request.classes if any('Controller' in ann for ann in c.annotations)])
        services = len([c for c in request.classes if any('Service' in ann for ann in c.annotations)])
        
        # Enhanced repository detection in fallback too
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

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Enhanced CodeScribe Backend")
    print("🧠 Features: Structured prompts, better parsing, enhanced analysis")
    uvicorn.run(app, host="0.0.0.0", port=8000)