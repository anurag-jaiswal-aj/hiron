import os
import json
import urllib.request
import urllib.error

def test_supabase_storage():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables are missing.")
        return

    bucket_name = "_hiron_storage_poc"
    test_file_path = f"poc/test_123/test.txt"
    test_content = b"Hiron Phase 20.2 Storage POC Test Content"
    
    base_storage_url = f"{supabase_url}/storage/v1"
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "apikey": supabase_key,
        "Content-Type": "application/json"
    }

    print("1. Checking/Creating Bucket...")
    try:
        # Create private bucket
        req = urllib.request.Request(
            f"{base_storage_url}/bucket",
            data=json.dumps({"id": bucket_name, "name": bucket_name, "public": False}).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req) as response:
            print("[PASS] Bucket created successfully.")
    except urllib.error.HTTPError as e:
        if e.code == 400 and b"already exists" in e.read():
            print("[PASS] Bucket already exists.")
        else:
            print(f"[FAIL] Bucket creation failed: {e}")
            return

    print("2. Uploading Test Object...")
    upload_headers = headers.copy()
    upload_headers["Content-Type"] = "text/plain"
    try:
        req = urllib.request.Request(
            f"{base_storage_url}/object/{bucket_name}/{test_file_path}",
            data=test_content,
            headers=upload_headers,
            method="POST"
        )
        with urllib.request.urlopen(req) as response:
            print("[PASS] Object uploaded successfully.")
    except urllib.error.HTTPError as e:
        print(f"[FAIL] Upload failed: {e.read()}")
        return

    print("3. Checking Object Existence...")
    try:
        req = urllib.request.Request(
            f"{base_storage_url}/object/info/public/{bucket_name}/{test_file_path}", 
            headers=headers,
            method="GET"
        )
        with urllib.request.urlopen(req) as response:
            print("[FAIL] Object is public (it should be private).")
    except urllib.error.HTTPError as e:
        if e.code == 404 or e.code == 400:
            print("[PASS] Object is confirmed private.")
        else:
            print(f"Unexpected error checking existence: {e}")

    print("4. Generating Signed URL...")
    signed_url = None
    try:
        req = urllib.request.Request(
            f"{base_storage_url}/object/sign/{bucket_name}/{test_file_path}",
            data=json.dumps({"expiresIn": 3600}).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            signed_url = f"{supabase_url}/storage/v1{data['signedURL']}"
            print("[PASS] Signed URL generated successfully.")
    except Exception as e:
        print(f"[FAIL] Signed URL generation failed: {e}")

    print("5. Downloading Object via Signed URL...")
    if signed_url:
        try:
            req = urllib.request.Request(signed_url, method="GET")
            with urllib.request.urlopen(req) as response:
                downloaded = response.read()
                if downloaded == test_content:
                    print("[PASS] Object downloaded and integrity verified.")
                else:
                    print("[FAIL] Content integrity mismatch.")
        except Exception as e:
            print(f"[FAIL] Download failed: {e}")

    print("6. Deleting Test Object...")
    try:
        req = urllib.request.Request(
            f"{base_storage_url}/object/{bucket_name}",
            data=json.dumps({"prefixes": [test_file_path]}).encode("utf-8"),
            headers=headers,
            method="DELETE"
        )
        with urllib.request.urlopen(req) as response:
            print("[PASS] Object deleted successfully.")
    except Exception as e:
        print(f"[FAIL] Deletion failed: {e}")

if __name__ == "__main__":
    test_supabase_storage()
