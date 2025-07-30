import httpx
from typing import Optional
from app.models import CodeAnalysisRequest

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
        controllers = [c for c in request.classes if any('Controller' in ann for ann in c.annotations)]
        services = [c for c in request.classes if any('Service' in ann for ann in c.annotations)]
        repositories = [c for c in request.classes if 
                       any('Repository' in ann for ann in c.annotations) or
                       c.name.endswith('Repository') or
                       any('JpaRepository' in ann or 'CrudRepository' in ann for ann in c.annotations)]
        entities = [c for c in request.classes if any('Entity' in ann for ann in c.annotations)]

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

        prompt = self.create_structured_prompt(request)
        print(f"🚀 Analyzing with {model}...")
        print(f"📝 Prompt length: {len(prompt)} chars")

        try:
            request_data = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 300,
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
                    return ai_response if ai_response else None
                else:
                    print(f"❌ HTTP {response.status_code}: {response.text}")
                    return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    async def ask_question(self, question: str, documentation_context: str) -> str:
        """Answer questions about the documentation using AI"""
        model = await self.get_available_model()
        if not model:
            print("❌ No model available for Q&A")
            return "❌ AI model unavailable. Please check Ollama service."

        # Create a focused prompt for Q&A
        prompt = f"""You are analyzing a Spring Boot project. Answer the user's question based on the documentation provided.

DOCUMENTATION CONTEXT:
{documentation_context}

USER QUESTION: {question}

Instructions:
- Provide a clear, concise answer based only on the provided documentation
- If the question asks for specific information (like counts, lists), be precise
- If the documentation doesn't contain the answer, say so clearly
- Keep responses focused and helpful

ANSWER:"""

        print(f"🤔 Processing Q&A with {model}...")
        print(f"❓ Question: {question}")
        print(f"📝 Context length: {len(documentation_context)} chars")

        try:
            request_data = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 200,  # Shorter responses for Q&A
                    "temperature": 0.3,  # Lower temperature for more factual responses
                    "top_p": 0.8
                }
            }

            print("📡 Sending Q&A prompt to Ollama...")
            async with httpx.AsyncClient(timeout=60.0) as client:  # Shorter timeout for Q&A
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json=request_data
                )

                print(f"📊 Q&A Status: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    ai_response = result.get("response", "").strip()
                    print(f"✅ Q&A Response: {len(ai_response)} chars")
                    
                    if ai_response:
                        return ai_response
                    else:
                        return "❌ AI returned empty response. Please try rephrasing your question."
                else:
                    print(f"❌ HTTP {response.status_code}: {response.text}")
                    return f"❌ AI service error (Status: {response.status_code}). Please try again."
                    
        except Exception as e:
            print(f"❌ Q&A Error: {e}")
            return f"❌ Connection error: {e}. Please check if Ollama is running."