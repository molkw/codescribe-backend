from pydantic import BaseModel
from typing import List, Optional

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

# New Q&A models
class QuestionRequest(BaseModel):
    question: str
    documentation_context: str

class QuestionResponse(BaseModel):
    answer: str
    processed_locally: bool = False