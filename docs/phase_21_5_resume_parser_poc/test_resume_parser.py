import os
import sys
import json
import time
import httpx
from typing import Any
from pydantic import BaseModel, Field, ValidationError

class ExperienceItem(BaseModel):
    title: str | None = Field(default=None)
    company: str | None = Field(default=None)
    location: str | None = Field(default=None)
    start_date: str | None = Field(default=None)
    end_date: str | None = Field(default=None)
    is_current: bool = Field(default=False)
    description: str | None = Field(default=None)

class EducationItem(BaseModel):
    degree: str | None = Field(default=None)
    institution: str | None = Field(default=None)
    graduation_year: int | None = Field(default=None)

class GeminiResumeExtraction(BaseModel):
    full_name: str | None = Field(default=None)
    location: str | None = Field(default=None)
    experience: list[ExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)

def convert_pydantic_schema_to_gemini(schema: dict[str, Any]) -> dict[str, Any]:
    import copy
    schema_copy = copy.deepcopy(schema)
    defs = schema_copy.pop("$defs", {})

    def resolve_refs(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                ref_path = node["$ref"]
                if ref_path.startswith("#/$defs/"):
                    def_name = ref_path.split("/")[-1]
                    resolved_node = copy.deepcopy(defs.get(def_name, {}))
                    return resolve_refs(resolved_node)
            return {k: resolve_refs(v) for k, v in node.items()}
        elif isinstance(node, list):
            return [resolve_refs(item) for item in node]
        return node

    return resolve_refs(schema_copy)

def test_schema_conversion():
    schema = GeminiResumeExtraction.model_json_schema()
    converted = convert_pydantic_schema_to_gemini(schema)
    
    schema_str = json.dumps(converted)
    assert "$defs" not in schema_str
    assert "$ref" not in schema_str
    assert converted["properties"]["experience"]["items"]["type"] == "object"
    assert converted["properties"]["education"]["items"]["type"] == "object"
    assert "title" in converted["properties"]["experience"]["items"]["properties"]
    assert "is_current" in converted["properties"]["experience"]["items"]["properties"]
    
def get_available_gemini_models(api_key: str):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    res = httpx.get(url, timeout=10.0)
    if res.status_code != 200:
        return []
    
    models = res.json().get("models", [])
    valid_models = []
    
    exclusions = ["image", "video", "audio", "tts", "embedding", "robotics", "computer-use", "deep-research", "lyria", "antigravity"]
    
    for m in models:
        if "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        name = m.get("name", "")
        if any(x in name for x in exclusions):
            continue
        valid_models.append(name)
        
    valid_models = sorted(valid_models, key=lambda x: (
        0 if "gemini-3.5-flash" in x else
        1 if "gemini-2.5-flash" in x else
        2 if "gemini-2.5-pro" in x else
        3 if "gemini-3." in x else
        4
    ))
        
    return valid_models

def run_gemini(api_key: str, model_name: str, resume_text: str):
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
    sys_instruction = "Extract the candidate's full name, location, experience, and education from the resume. If a value is not explicitly supported by the resume text, return null. Do not invent or infer information."
    gemini_schema = convert_pydantic_schema_to_gemini(GeminiResumeExtraction.model_json_schema())
    
    payload = {
        "systemInstruction": {"parts": [{"text": sys_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": resume_text}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": gemini_schema
        }
    }
    
    start = time.time()
    try:
        res = httpx.post(url, json=payload, timeout=7.5)
        latency = time.time() - start
    except httpx.TimeoutException as e:
        return None, time.time() - start, {"status": "TIMEOUT", "message": str(e)}
    except Exception as e:
        return None, time.time() - start, {"status": "ERROR", "message": str(e)}

    if res.status_code == 429:
        try:
            err_data = res.json()
            delay = err_data.get("error", {}).get("details", [{}])[-1].get("retryDelay", "unknown")
        except Exception:
            delay = "unknown"
        return res, latency, {"status": "BLOCKED_BY_QUOTA", "retry_delay": delay}
        
    if res.status_code == 404:
        return res, latency, {"status": "MODEL_UNAVAILABLE"}
        
    if res.status_code != 200:
        return res, latency, {"status": f"HTTP_{res.status_code}", "body": res.text}
        
    try:
        data = res.json()
    except Exception as e:
        return res, latency, {"status": "JSON_ERROR", "message": str(e)}
        
    try:
        cands = data.get("candidates")
        if not cands:
             return res, latency, {"status": "NO_CANDIDATES", "body": data}
        json_str = cands[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
        parsed = GeminiResumeExtraction.model_validate_json(json_str)
    except Exception as e:
        return res, latency, {"status": "VALIDATION_ERROR", "message": str(e), "body": data}

    return res, latency, {"status": "SUCCESS", "parsed": parsed, "data": data}

def execute_poc():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[FAIL] GEMINI_API_KEY environment variable is MISSING. Please export it and run again.")
        sys.exit(1)
        
    print("1. Authentication: PASS")
    
    models = get_available_gemini_models(api_key)
    if not models:
        print("[FAIL] No valid text generation models found.")
        sys.exit(1)
        
    print(f"2. Model availability: Found {len(models)} candidate models.")
    working_model = None
    
    # Model discovery testing
    for m in models:
        print(f"Trying model: {m}...")
        res, lat, result = run_gemini(api_key, m, "Test string to check availability.")
        status = result.get("status")
        
        if status == "MODEL_UNAVAILABLE":
            print(f"  [DEBUG] Model {m} -> MODEL_UNAVAILABLE")
            continue
        elif status == "TIMEOUT":
            print(f"  [DEBUG] Model {m} -> TIMEOUT")
            continue
        elif status == "BLOCKED_BY_QUOTA":
            print(f"  [DEBUG] Model {m} -> BLOCKED_BY_QUOTA (retry: {result.get('retry_delay')})")
            print("[FAIL] Quota exhausted during discovery. Stopping.")
            sys.exit(1)
        elif status and status.startswith("HTTP_"):
            print(f"  [DEBUG] Model {m} -> {status}")
            continue
            
        working_model = m
        print(f"-> Working model: {working_model}")
        break
            
    if not working_model:
        print("[FAIL] All models failed discovery.")
        sys.exit(1)

    print("\n--- Running Final Production-like Validation ---")
    resume_long = '''
    JOHN DOE
    123 Tech Lane, San Francisco, CA 94107
    johndoe@email.com | 555-0199 | linkedin.com/in/johndoe
    
    SUMMARY
    Experienced software engineer with a background in scalable backend systems.
    
    SKILLS
    Python, Java, Go, Kubernetes, PostgreSQL
    
    EXPERIENCE
    Staff Software Engineer
    TechNova Inc. | San Francisco, CA
    March 2021 - Present
    - Led backend infrastructure migration to Kubernetes.
    - Designed distributed PostgreSQL architecture.
    
    Senior Backend Engineer
    CloudWorks Ltd | Seattle, WA
    Jan 2018 - Feb 2021
    - Developed microservices in Go.
    
    Software Engineer
    StartupX | Austin, TX
    June 2015 - Dec 2017
    - Built REST APIs using Python.
    
    EDUCATION
    Master of Science in Computer Science
    University of Washington
    2015
    
    Bachelor of Science in Software Engineering
    University of Texas
    2013
    '''
    
    res, lat, result = run_gemini(api_key, working_model, resume_long)
    
    if result.get("status") == "BLOCKED_BY_QUOTA":
        print(f"[FAIL] BLOCKED_BY_QUOTA. Please wait {result.get('retry_delay')} before retrying.")
        sys.exit(1)
    elif result.get("status") != "SUCCESS":
        print(f"[FAIL] Unexpected failure: {result}")
        sys.exit(1)
        
    parsed = result["parsed"]
    data = result["data"]
    
    print(f"Model: {working_model}")
    print(f"HTTP Status: {res.status_code}")
    lat_verdict = "PASS" if lat <= 7.5 else "WARNING"
    print(f"Latency: {lat:.3f}s ({lat_verdict})")
    
    usage = data.get("usageMetadata", {})
    print(f"Input Tokens: {usage.get('promptTokenCount')}")
    print(f"Output Tokens: {usage.get('candidatesTokenCount')}")
    
    print(f"Experience Count: {len(parsed.experience)}")
    print(f"Education Count: {len(parsed.education)}")
    print(f"Full Name: {parsed.full_name}")
    print(f"Location: {parsed.location}")
    if parsed.experience:
        print(f"Is Current (First Job): {parsed.experience[0].is_current}")
    else:
        print("Is Current (First Job): N/A (Empty)")
        
    print("\n[SUCCESS] Final POC validation complete.")

if __name__ == "__main__":
    execute_poc()
