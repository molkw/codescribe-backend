from app.models import CodeAnalysisRequest, AIDocumentationResponse

def parse_structured_response(ai_response: str, request: CodeAnalysisRequest) -> AIDocumentationResponse:
    controllers = len([c for c in request.classes if any('Controller' in ann for ann in c.annotations)])
    services = len([c for c in request.classes if any('Service' in ann for ann in c.annotations)])
    repositories = len([c for c in request.classes if 
                       any('Repository' in ann for ann in c.annotations) or
                       c.name.endswith('Repository') or
                       any('JpaRepository' in ann or 'CrudRepository' in ann for ann in c.annotations)])
    entities = len([c for c in request.classes if any('Entity' in ann for ann in c.annotations)])

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

        if current_section == 'overview':
            sections['overview'] += line + ' '
        elif current_section == 'architecture':
            sections['architecture'] += line + ' '
        elif current_section in ['key_insights', 'suggestions', 'patterns']:
            if line.startswith(('-', '*', '•')):
                sections[current_section].append(line.lstrip('-•* '))
            elif line and not line.isupper():
                sections[current_section].append(line)

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

    architectural_patterns = []
    if controllers > 0 and services > 0:
        architectural_patterns.append("Spring Boot MVC")
    if services > 0 and repositories > 0:
        architectural_patterns.append("Layered Architecture")
    if repositories > 0:
        architectural_patterns.append("Repository Pattern")

    architectural_patterns.extend(sections['patterns'])

    return AIDocumentationResponse(
        documentation=documentation,
        insights=sections['key_insights'] or ["AI analysis completed successfully"],
        suggestions=sections['suggestions'] or ["Consider adding integration tests"],
        architectural_patterns=list(set(architectural_patterns))
    )
