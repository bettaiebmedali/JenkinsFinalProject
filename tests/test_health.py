import requests

def test_health():
    r = requests.get("http://localhost:8080/health", timeout=5)
    assert r.status_code == 200
    assert r.json().get("status") == "OK"
