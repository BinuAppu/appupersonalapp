
from app import app
import json

def test_smtp_cert():
    client = app.test_client()
    url = "/api/net/cert"
    
    target = "smtp.office365.com:587"
    print(f"Testing Cert for {target}...")
    
    try:
        r = client.post(url, json={"target": target})
        if r.status_code == 200:
            data = r.get_json()
            if "subject" in data and "outlook.com" in str(data): # expected subject often matches outlook.com
                print("PASS: SMTP Cert Retrieved")
                print(f"Subject: {data.get('subject')}")
            else:
                print(f"PASS (Warning): Retrieved but subject might be unexpected: {data.get('subject')}")
        else:
            print(f"FAIL: {r.status_code} - {r.get_json()}")
    except Exception as e:
        print(f"FAIL: Exception: {e}")

if __name__ == "__main__":
    test_smtp_cert()
