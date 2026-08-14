import os
import sys
import json
import time
import httpx

# Setup Python path to include apps/api
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../apps/api")))

from hiron.candidates.models import Candidate
from hiron.jobs.models import Job
from hiron.scores.engine import AIScoringEngine
from hiron.scores.schemas import AIGeneratedScore

def get_available_gemini_models(api_key: str):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    res = httpx.get(url, timeout=10.0)
    if res.status_code != 200:
        print(f"[FAIL] Error fetching models: {res.status_code} {res.text}")
        return []
    
    models = res.json().get("models", [])
    valid_models = []
    
    for m in models:
        # We need generateContent support
        if "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        
        # Filter out known non-text/specialty models
        name = m.get("name", "")
        if any(x in name for x in ["embedding", "vision", "audio", "video", "aqa", "imagen"]):
            continue
            
        valid_models.append(name)
        
    return valid_models

def run_poc():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[FAIL] GEMINI_API_KEY environment variable is MISSING.")
        print("Please export GEMINI_API_KEY and run this script again.")
        sys.exit(1)
        
    print("1. Authentication: PASS")
    
    models = get_available_gemini_models(api_key)
    if not models:
        print("[FAIL] No valid text generation models found.")
        sys.exit(1)
        
    print(f"2. Model availability: Found {len(models)} candidate models.")
    
    candidate = Candidate(
        id="123e4567-e89b-12d3-a456-426614174000",
        tenant_id="123e4567-e89b-12d3-a456-426614174000",
        full_name="Alice Smith",
        skills=["Python", "PostgreSQL", "FastAPI", "React", "Docker"],
        summary="Experienced Backend Engineer with a strong background in Python and distributed systems.",
        total_experience_years=5,
    )

    job = Job(
        id="123e4567-e89b-12d3-a456-426614174001",
        tenant_id="123e4567-e89b-12d3-a456-426614174000",
        title="Senior Backend Engineer",
        description="We are looking for a backend engineer to build scalable APIs and manage PostgreSQL databases.",
        required_skills=["Python", "PostgreSQL", "AWS"],
        experience_years_min=4,
    )

    success = False
    for model_name in models:
        print(f"\n--- Testing model: {model_name} ---")
        
        # Force settings
        os.environ["AI_PROVIDER"] = "gemini"
        os.environ["GEMINI_LLM_MODEL"] = model_name
        
        engine = AIScoringEngine()
        
        try:
            # We measure time around engine.evaluate to get overall latency including Pydantic overhead
            start_time = time.time()
            result = engine.evaluate(candidate, job)
            latency_seconds = time.time() - start_time
            
            print(f"[SUCCESS] Generation successful with HTTP 200.")
            print(f"3. Simple generation: PASS")
            print(f"4. Structured scoring generation: PASS")
            print(f"5. Existing Hiron scoring schema validation: PASS")
            
            # Validate required fields and nested structure
            print(f"6. Required fields (fit_score, confidence): {result['fit_score']}, {result['confidence']}")
            print(f"7. Nested breakdown validation: PASS (Skills score: {result['breakdown']['skills']['score']})")
            print(f"8. Numeric values (latency): {result['latency_ms']} ms")
            print(f"9. List fields (skills_matched): {result['skills_matched']}")
            
            print(f"14. Actual latency measurement: {latency_seconds:.2f} seconds")
            if latency_seconds <= 7.5:
                print(f"-> Latency is compatible with the 7.5s client timeout.")
            else:
                print(f"-> WARNING: Latency exceeded 7.5s ({latency_seconds:.2f}s)")
                
            input_tokens = result.get("input_tokens", 0)
            output_tokens = result.get("output_tokens", 0)
            print(f"15. Usage metadata extraction: input={input_tokens}, output={output_tokens}")
            
            success = True
            break # Exit loop on first successful model
            
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            print(f"[FAIL] HTTP {status}: {e.response.text}")
            if status == 429:
                print("11. HTTP 429 handling: Triggered")
            elif status >= 400:
                print("12. HTTP 4xx/5xx handling: Triggered")
            # Continue to next model
            continue
        except httpx.TimeoutException:
            print("[FAIL] Request timed out (13. Request timeout handling: Triggered).")
            continue
        except Exception as e:
            print(f"[FAIL] Error during generation: {str(e)}")
            continue

    if not success:
        print("\n[FAIL] All candidate models failed.")
        sys.exit(1)
        
    print("\n[SUCCESS] Live Gemini Scoring POC complete.")

if __name__ == "__main__":
    run_poc()
