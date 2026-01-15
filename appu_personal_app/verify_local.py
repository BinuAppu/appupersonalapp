
import sys
import os
import json

# Add the app directory to sys.path
sys.path.append(os.getcwd())

from app import app

def test_connectivity_logic():
    client = app.test_client()
    
    # Test 1: Single IP, Single Port
    payload = {
        "ips": "8.8.8.8",
        "ports": "53",
        "protocol": "TCP",
        "timeout": 1
    }
    print(f"Testing {payload}...")
    res = client.post('/api/net/check', json=payload)
    print(f"Status: {res.status_code}")
    print(f"Response: {res.get_json()}")
    
    # Test 2: Multiple IPs, Multiple Ports
    payload = {
        "ips": "8.8.8.8, 1.1.1.1",
        "ports": "53, 443",
        "protocol": "TCP",
        "timeout": 1
    }
    print(f"\nTesting {payload}...")
    res = client.post('/api/net/check', json=payload)
    print(f"Status: {res.status_code}")
    print(f"Response: {res.get_json()}")

    # Test 3: Manual Timeout (fake IP)
    payload = {
        "ips": "192.0.2.0", # Test-Net-1, should be unreachable
        "ports": "80", 
        "timeout": 0.5
    }
    print(f"\nTesting Timeout {payload}...")
    from time import time
    start = time()
    res = client.post('/api/net/check', json=payload)
    print(f"Elapsed: {time() - start:.2f}s")
    print(f"Response: {res.get_json()}")

if __name__ == "__main__":
    test_connectivity_logic()
