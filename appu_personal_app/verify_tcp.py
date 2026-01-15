
import requests
import time

BASE_URL = "http://127.0.0.1:5000"

def test_connectivity():
    url = f"{BASE_URL}/api/net/check"
    
    # Test 1: Single IP, Single Port
    payload = {
        "ips": "8.8.8.8",
        "ports": "53",
        "protocol": "TCP",
        "timeout": 1
    }
    print(f"Testing {payload}...")
    try:
        r = requests.post(url, json=payload, timeout=5)
        print(r.status_code)
        print(r.json())
    except Exception as e:
        print(f"Error: {e}")

    # Test 2: Multiple IPs, Multiple Ports (Ranges)
    payload = {
        "ips": "8.8.8.8, 1.1.1.1",
        "ports": "53, 443",
        "protocol": "TCP", 
        "timeout": 1
    }
    print(f"\nTesting {payload}...")
    try:
        r = requests.post(url, json=payload, timeout=5)
        print(r.status_code)
        print(r.json())
    except Exception as e:
        print(f"Error: {e}")
        
    # Test 3: Manual Timeout logic check (fake IP to force timeout)
    payload = {
        "ips": "192.168.123.123", # Likely unreachable
        "ports": "80", 
        "timeout": 0.5
    }
    print(f"\nTesting Timeout {payload}...")
    start = time.time()
    try:
        r = requests.post(url, json=payload, timeout=5)
        print(f"Elapsed: {time.time() - start:.2f}s")
        print(r.json())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_connectivity()
