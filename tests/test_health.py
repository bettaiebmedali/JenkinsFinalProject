import requests

BASE_URL = "http://127.0.0.1:8888"  # hardcodé pour Jenkins pipeline

def test_health():
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    assert r.status_code == 200
    assert r.json().get("status") is True
