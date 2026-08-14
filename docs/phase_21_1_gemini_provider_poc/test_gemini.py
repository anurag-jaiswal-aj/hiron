import os
import sys
import json
import httpx
import time

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[FAIL] GEMINI_API_KEY environment variable is MISSING.")
        print("Please export GEMINI_API_KEY and run this script again.")
        sys.exit(1)

    print("[PASS] GEMINI_API_KEY is SET.")
    
    headers = {
        "Content-Type": "application/json"
    }

    # 1. Fetch available models
    print("\n--- 1. Fetching Available Models ---")
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    generation_candidates = []
    embedding_model = "models/gemini-embedding-001" # Keep known good
    
    try:
        res = httpx.get(list_url, timeout=10.0)
        if res.status_code == 200:
            models = res.json().get("models", [])
            print(f"Found {len(models)} models.")
            for m in models:
                name = m.get("name")
                methods = m.get("supportedGenerationMethods", [])
                
                # Identify generation candidates
                if "generateContent" in methods or "interactContent" in methods:
                    if any(exclude in name for exclude in ["image", "audio", "video", "embedding", "vision"]):
                        continue
                    if "flash" in name:
                        generation_candidates.append({
                            "name": name,
                            "display_name": m.get("displayName", ""),
                            "methods": methods
                        })
        else:
            print(f"[FAIL] Failed to list models. Status: {res.status_code}, Body: {res.text}")
            sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Exception fetching models: {e}")
        sys.exit(1)

    if not generation_candidates:
        print("[FAIL] Could not find any valid text-generation models.")
        sys.exit(1)

    # Sort candidates preferring 3.6, 3.5, 3.1, etc.
    def score_model(m):
        score = 0
        if "3.6" in m["name"]: score += 100
        elif "3.5" in m["name"]: score += 90
        elif "3.1" in m["name"]: score += 80
        elif "3.0" in m["name"]: score += 70
        if "lite" not in m["name"]: score += 5  # prefer non-lite if available
        return score
    
    generation_candidates.sort(key=score_model, reverse=True)

    print("\nTop 5 Generation Candidates:")
    for c in generation_candidates[:5]:
        print(f"  - {c['name']} (Methods: {c['methods']})")

    # 2. Simple Text Generation with Fallback
    print("\n--- 2. Simple Text Generation (Testing Candidates) ---")
    
    successful_model = None
    successful_methods = None
    
    for candidate in generation_candidates:
        model_name = candidate["name"]
        print(f"\nTrying model: {model_name} ...")
        
        # Test generateContent
        generate_url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": "Reply with exactly: Hiron Gemini POC PASS"}]}]
        }
        
        start = time.time()
        try:
            res = httpx.post(generate_url, headers=headers, json=payload, timeout=10.0)
            latency = int((time.time() - start) * 1000)
            
            if res.status_code == 200:
                data = res.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                usage = data.get("usageMetadata", {})
                print(f"[PASS] Generation Successful on {model_name}! Latency: {latency}ms")
                print(f"       Response: {text}")
                print(f"       Usage: {usage}")
                successful_model = model_name
                successful_methods = candidate["methods"]
                break
            else:
                print(f"[FAIL] {model_name} failed. Status: {res.status_code}")
                try:
                    print(f"       Error: {res.json().get('error', {}).get('message')}")
                except:
                    print(f"       Body: {res.text}")
        except Exception as e:
            print(f"[FAIL] Exception testing {model_name}: {e}")

    if not successful_model:
        print("\n[CRITICAL FAIL] ALL generation candidates failed. Zero usable free-tier text generation models found.")
        sys.exit(1)

    print(f"\n>>> FINAL SELECTED MODEL: {successful_model}")
    print(f">>> SUPPORTED METHODS: {successful_methods}")

    # 3. Structured JSON Generation
    print("\n--- 3. Structured JSON Generation ---")
    schema = {
        "type": "OBJECT",
        "properties": {
            "full_name": {"type": "STRING"},
            "skills": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            }
        },
        "required": ["full_name", "skills"]
    }
    
    structured_payload = {
        "contents": [{"parts": [{"text": "John Doe\nSoftware Engineer\nSkills: Python, React, Postgres"}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": schema
        }
    }
    
    generate_url = f"https://generativelanguage.googleapis.com/v1beta/{successful_model}:generateContent?key={api_key}"
    
    start = time.time()
    try:
        res = httpx.post(generate_url, headers=headers, json=structured_payload, timeout=10.0)
        latency = int((time.time() - start) * 1000)
        
        if res.status_code == 200:
            data = res.json()
            json_text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(json_text)
            print(f"[PASS] Structured JSON Generation Successful. Latency: {latency}ms")
            print(f"       Parsed: {parsed}")
            print(f"       Usage: {data.get('usageMetadata', {})}")
        else:
            print(f"[FAIL] Structured generation failed. Status: {res.status_code}, Body: {res.text}")
    except Exception as e:
        print(f"[FAIL] Exception during structured generation: {e}")

    # 4. Embedding Generation and Dimensionality Check (PRESERVED)
    print("\n--- 4. Embedding Generation & Dimensionality ---")
    embed_url = f"https://generativelanguage.googleapis.com/v1beta/{embedding_model}:embedContent?key={api_key}"
    embed_payload = {
        "model": embedding_model,
        "content": {
            "parts": [{"text": "This is a test for embeddings."}]
        },
        "outputDimensionality": 1536
    }
    
    start = time.time()
    try:
        res = httpx.post(embed_url, headers=headers, json=embed_payload, timeout=10.0)
        latency = int((time.time() - start) * 1000)
        
        if res.status_code == 200:
            data = res.json()
            embedding = data["embedding"]["values"]
            dimensions = len(embedding)
            print(f"[PASS] Embedding Generation Successful. Latency: {latency}ms")
            print(f"       Dimensionality Returned: {dimensions}")
            if dimensions == 1536:
                print("       [PASS] 1536 dimensions achieved! Fully compatible with Hiron's vector(1536) schema.")
            else:
                print(f"       [WARN] Hiron expects 1536 dimensions, got {dimensions}.")
        else:
            print(f"[FAIL] Embedding failed. Status: {res.status_code}, Body: {res.text}")
    except Exception as e:
        print(f"[FAIL] Exception during embedding: {e}")

if __name__ == "__main__":
    main()
