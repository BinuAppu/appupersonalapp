
from app import app
import json

def test_connectivity_protocol():
    client = app.test_client()
    url = "/api/net/check"
    
    # Test UDP
    payload_udp = {
        "ips": "8.8.8.8",
        "ports": "53",
        "protocol": "UDP",
        "timeout": 1
    }
    print("Testing UDP Check...")
    try:
        r = client.post(url, json=payload_udp)
        data = r.get_json()
        if "results" in data and data["results"][0].get("protocol") == "UDP":
            print("PASS: Protocol returned as UDP")
        else:
            print(f"FAIL: Protocol check failed. Got {data}")
    except Exception as e:
        print(f"FAIL: UDP Check Error: {e}")

    # Test TCP
    payload_tcp = {
        "ips": "google.com",
        "ports": "80",
        "protocol": "TCP",
        "timeout": 1
    }
    print("\nTesting TCP Check...")
    try:
        r = client.post(url, json=payload_tcp)
        data = r.get_json()
        if "results" in data and data["results"][0].get("protocol") == "TCP":
            print("PASS: Protocol returned as TCP")
        else:
            print(f"FAIL: Protocol check failed. Got {data}")
    except Exception as e:
        print(f"FAIL: TCP Check Error: {e}")

def test_cert_details():
    client = app.test_client()
    url = "/api/net/cert"
    
    # Test 1: Full URL
    target_url = "https://google.com"
    print(f"\nTesting Cert with URL: {target_url}...")
    try:
        r = client.post(url, json={"target": target_url})
        data = r.get_json()
        if "sans" in data and len(data["sans"]) > 0:
            print("PASS: SANs found")
        else:
            print("FAIL: SANs missing")
            
        if "notBefore" in data and "-" in data["notBefore"] and ":" in data["notBefore"]:
             print(f"PASS: Date formatted correctly ({data['notBefore']})")
        else:
             print(f"FAIL: Date format incorrect: {data.get('notBefore')}")
             
    except Exception as e:
        print(f"FAIL: Cert URL Check Error: {e}")

    # Test 2: Host Only
    target_host = "google.com"
    print(f"\nTesting Cert with Host: {target_host}...")
    try:
        r = client.post(url, json={"target": target_host})
        if r.status_code == 200:
            print("PASS: Host only worked")
        else:
            print(f"FAIL: Host only failed {r.get_json()}")
    except Exception as e:
        print(f"FAIL: Cert Host Check Error: {e}")

    # Test 3: IP:Port
    target_port = "8.8.8.8:443" # Google DNS
    print(f"\nTesting Cert with Host:Port: {target_port}...")
    try:
        r = client.post(url, json={"target": target_port})
        if r.status_code == 200:
            data = r.get_json()
            # print(data) # Debug if needed
            print("PASS: Host:Port worked")
        else:
             # It might fail if no cert on 8.8.8.8:443, but usually there is DOH or similar. 
             # If it fails due to network, that's okay, but we want to check parsing logic mostly.
             # Actually 8.8.8.8:443 supports DoH.
            print(f"FAIL: Host:Port failed {r.get_json()}")
    except Exception as e:
        print(f"FAIL: Cert Host:Port Check Error: {e}")

if __name__ == "__main__":
    test_connectivity_protocol()
    test_cert_details()
