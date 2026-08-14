#!/usr/bin/env python3
"""
Test script to verify real QStash delivery.
Must be run with QSTASH_TOKEN and a publicly reachable WEBHOOK_URL.
"""
import os
import sys
import uuid
from qstash import QStash

def main() -> None:
    token = os.environ.get("QSTASH_TOKEN")
    current_key = os.environ.get("QSTASH_CURRENT_SIGNING_KEY")
    webhook_url = os.environ.get("WEBHOOK_URL")

    if not token or not current_key:
        print("Error: QSTASH_TOKEN and QSTASH_CURRENT_SIGNING_KEY must be set.")
        sys.exit(1)

    if not webhook_url:
        print("Error: WEBHOOK_URL must be set (e.g. https://your-ngrok-url.app/api/v1/webhooks/qstash/test)")
        sys.exit(1)

    print("Initializing QStash client...")
    client = QStash(token)
    
    payload = {
        "event": "phase_21_6_3_test",
        "message_id": str(uuid.uuid4()),
        "payload": {
            "hello": "qstash_real_delivery"
        }
    }
    
    print(f"Publishing ONE test message to {webhook_url}...")
    try:
        res = client.message.publish_json(
            url=webhook_url,
            body=payload,
            deduplication_id=payload["message_id"],
        )
        print("✅ Publish success!")
        print(f"Message ID: {res.message_id}")
        print(f"Destination: {webhook_url}")
        print("\nIMPORTANT: Please check your local server logs to verify delivery, HTTP status, and signature validation.")
    except Exception as e:
        print(f"❌ Publish failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
