from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "SecureMe backend is running!"}

def test_check_password_weak():
    response = client.post("/check-password", json={"password": "weak"})
    assert response.status_code == 200
    data = response.json()
    assert data["strength"] == "Weak ❌"

def test_check_password_strong():
    response = client.post("/check-password", json={"password": "StrongPassword123!"})
    assert response.status_code == 200
    data = response.json()
    assert data["strength"] == "Strong 💪"

def test_scan_apps_safe():
    response = client.post("/scan-apps", json={"apps": ["com.google.android.youtube", "com.whatsapp"]})
    assert response.status_code == 200
    data = response.json()
    assert data["risky_count"] == 0
    assert "All apps are safe!" in data["status"]

def test_scan_apps_risky():
    response = client.post("/scan-apps", json={"apps": ["com.fake.spyware"]})
    assert response.status_code == 200
    data = response.json()
    assert data["risky_count"] == 1
    assert data["risky_apps"][0]["package"] == "com.fake.spyware"

def test_cyber_health_score_good():
    response = client.post("/cyber-health-score", json={"password": "StrongPassword123!", "installed_apps": []})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Safe ✅"

def test_cyber_health_score_bad():
    response = client.post("/cyber-health-score", json={"password": "weak", "installed_apps": ["com.fake.spyware"]})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "High Risk ❌"

def test_analyze_permissions_critical():
    response = client.post("/analyze-permissions", json={"apps": [{"name": "FakeApp", "package": "com.fake", "permissions": ["android.permission.ACCESS_FINE_LOCATION"]*16}]})
    assert response.status_code == 200
    data = response.json()
    assert data["risky_apps_count"] > 0
    assert data["overall_risk"] in ["High", "Medium", "Low"]
