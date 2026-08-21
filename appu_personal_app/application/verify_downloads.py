import requests
import csv
import io

BASE_URL = "http://127.0.0.1:8000"

def test_download(endpoint, filename, expected_headers):
    print(f"Testing {endpoint}...")
    try:
        response = requests.get(f"{BASE_URL}{endpoint}")
        if response.status_code != 200:
            print(f"FAILED: Status code {response.status_code}")
            return False
        
        if 'text/csv' not in response.headers.get('Content-Type', ''):
            print(f"FAILED: Content-Type {response.headers.get('Content-Type')}")
            return False
            
        if filename not in response.headers.get('Content-Disposition', ''):
            print(f"FAILED: Content-Disposition {response.headers.get('Content-Disposition')}")
            return False
            
        # Verify CSV headers
        stream = io.StringIO(response.text)
        reader = csv.reader(stream)
        headers = next(reader)
        if headers != expected_headers:
            print(f"FAILED: Headers mismatch. Expected {expected_headers}, got {headers}")
            return False
            
        print(f"PASSED: {filename} downloaded correctly.")
        return True
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    # Check if server is running
    try:
        requests.get(BASE_URL)
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Server not running at {BASE_URL}. Please start the server first.")
        exit(1)

    success = True
    success &= test_download('/api/reminders/download', 'reminders_export.csv', ['id', 'title', 'description', 'date', 'recurrence', 'start_time', 'end_time', 'created_at'])
    success &= test_download('/api/tasks/download', 'tasks_export.csv', ['id', 'title', 'description', 'status', 'created_at'])
    success &= test_download('/api/projects/download', 'projects_export.csv', ['id', 'name', 'description', 'start_date', 'end_date', 'status', 'created_at'])

    if success:
        print("\nAll download tests PASSED!")
    else:
        print("\nSome download tests FAILED.")
