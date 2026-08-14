import os
import json
import httpx
import hmac
import hashlib
import base64
import time

def verify_qstash_signature(body: str, signature: str, current_key: str, next_key: str) -> bool:
    """Mock verification of a QStash signature.
    In production, this would use the upstash-qstash Receiver, but for the POC
    we verify we can process the signing keys.
    """
    # In a real scenario, the signature is a JWT that we verify using the signing keys.
    # We won't fully implement JWT verification here to avoid requiring `pyjwt` if not installed,
    # but we will check if the keys are present and have correct format.
    if not current_key.startswith("sig_") or not next_key.startswith("sig_"):
        return False
    return True

def test_upstash_qstash():
    qstash_token = os.getenv("QSTASH_TOKEN")
    current_key = os.getenv("QSTASH_CURRENT_SIGNING_KEY")
    next_key = os.getenv("QSTASH_NEXT_SIGNING_KEY")

    if not qstash_token or not current_key or not next_key:
        print("ERROR: Missing one or more required QStash environment variables.")
        return

    print("1. Validating QStash Credentials...")
    if not qstash_token.startswith("ey"):
        print("[WARN] QStash token format looks unusual, but proceeding.")
    print("[PASS] Credentials loaded successfully.")

    # Target URL for the POC - use postman-echo to deterministically return 200 OK
    target_url = "https://postman-echo.com/post"
    
    headers = {
        "Authorization": f"Bearer {qstash_token}",
        "Content-Type": "application/json",
        "Upstash-Forward-My-Custom-Header": "Hiron-POC"
    }

    payload = {
        "job_id": "poc-test-123",
        "action": "parse_resume"
    }

    print("2. Publishing Background Job to QStash...")
    message_id = None
    try:
        # The QStash REST API endpoint to publish a message
        # Format: POST https://qstash.upstash.io/v2/publish/URL
        res = httpx.post(
            f"https://qstash.upstash.io/v2/publish/{target_url}",
            headers=headers,
            json=payload,
            timeout=10.0
        )
        
        if res.status_code in (200, 201, 202):
            data = res.json()
            message_id = data.get("messageId")
            print(f"[PASS] Message published successfully. Message ID: {message_id}")
        else:
            print(f"[FAIL] Failed to publish message. Status: {res.status_code}, Body: {res.text}")
            return
    except Exception as e:
        print(f"[FAIL] Error publishing message: {e}")
        return

    print("3. Simulating Signature Verification (Security)...")
    if verify_qstash_signature("mock_body", "mock_sig", current_key, next_key):
        print("[PASS] Signature keys are correctly formatted and accessible.")
    else:
        print("[FAIL] Signature key validation failed.")

    print("4. Fetching Event Delivery Status (Waiting for QStash)...")
    # QStash provides an events API to check what happened to the message.
    # Delivery is asynchronous, so we poll up to 10 times with a 2-second delay.
    max_retries = 10
    delivered = False
    
    for attempt in range(max_retries):
        time.sleep(2)
        try:
            res = httpx.get(
                "https://qstash.upstash.io/v2/events",
                headers={"Authorization": f"Bearer {qstash_token}"}
            )
            if res.status_code == 200:
                events = res.json().get("events", [])
                found_event = next((e for e in events if e.get("messageId") == message_id), None)
                
                if found_event:
                    state = found_event.get("state")
                    if state == "DELIVERED":
                        print(f"[PASS] Event delivered successfully! (State={state})")
                        delivered = True
                        break
                    elif state == "ERROR":
                        error_msg = found_event.get("error", "Unknown error")
                        print(f"[FAIL] Event delivery failed according to QStash. Error: {error_msg}")
                        return
                    else:
                        error_msg = found_event.get("error", "No error string provided")
                        print(f"       Still processing (State={state}). Reason: {error_msg}. Retrying...")
                else:
                    print(f"       Message not yet in event log, retrying... (Attempt {attempt+1}/{max_retries})")
            else:
                print(f"[FAIL] Failed to fetch events. Status: {res.status_code}")
                return
        except Exception as e:
            print(f"[FAIL] Error fetching events: {e}")
            return
            
    if not delivered:
        print("[FAIL] Timeout waiting for QStash event delivery confirmation.")

if __name__ == "__main__":
    test_upstash_qstash()
