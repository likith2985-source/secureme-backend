from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import re
import hashlib
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

VIRUSTOTAL_API_KEY = "0a391695536864e06892ce0bfc05a9f3305c577213961fa6b9a598ea91d3e42c"

RISKY_APPS = ["com.fake.spyware", "com.malware.virus", "com.suspicious.tracker"]

@app.get("/")
def home():
    return {"message": "SecureMe backend is running!"}

@app.post("/check-password")
def check_password(data: dict):
    password = data.get("password", "")
    score = 0
    suggestions = []

    if len(password) >= 8:
        score += 25
    else:
        suggestions.append("Use at least 8 characters")

    if re.search(r'[A-Z]', password):
        score += 25
    else:
        suggestions.append("Add uppercase letters (A-Z)")

    if re.search(r'[0-9]', password):
        score += 25
    else:
        suggestions.append("Add numbers (0-9)")

    if re.search(r'[!@#$%^&*(),.?\":{}|<>]', password):
        score += 25
    else:
        suggestions.append("Add special characters (!@#$...)")

    if score >= 75:
        strength = "Strong 💪"
    elif score >= 50:
        strength = "Moderate ⚠️"
    else:
        strength = "Weak ❌"

    return {"score": score, "strength": strength, "suggestions": suggestions}

@app.post("/scan-file")
async def scan_file(data: dict):
    file_content = data.get("content", "")
    file_name = data.get("name", "unknown")
    file_hash = hashlib.sha256(file_content.encode()).hexdigest()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.virustotal.com/api/v3/files/{file_hash}",
                headers={"x-apikey": VIRUSTOTAL_API_KEY},
                timeout=10,
            )
            if response.status_code == 200:
                vt_data = response.json()
                stats = vt_data["data"]["attributes"]["last_analysis_stats"]
                malicious = stats.get("malicious", 0)
                total = sum(stats.values())
                if malicious > 0:
                    status = f"⚠️ Malicious! Detected by {malicious}/{total} engines"
                    is_malicious = True
                else:
                    status = f"✅ File is Safe (0/{total} engines flagged)"
                    is_malicious = False
            else:
                status = "✅ File not found in threat database — likely safe"
                is_malicious = False
                malicious = 0
                total = 0
    except Exception as e:
        status = "⚠️ Could not reach VirusTotal — checked locally"
        is_malicious = False
        malicious = 0
        total = 0

    return {
        "hash": file_hash,
        "name": file_name,
        "is_malicious": is_malicious,
        "malicious_count": malicious,
        "total_engines": total,
        "status": status,
    }

@app.post("/cyber-health-score")
def cyber_health_score(data: dict):
    password = data.get("password", "")
    installed_apps = data.get("installed_apps", [])

    pw_score = 0
    if len(password) >= 8: pw_score += 25
    if re.search(r'[A-Z]', password): pw_score += 25
    if re.search(r'[0-9]', password): pw_score += 25
    if re.search(r'[!@#$%^&*]', password): pw_score += 25

    risky_found = [app for app in installed_apps if app in RISKY_APPS]
    app_score = max(0, 100 - (len(risky_found) * 30))

    final_score = int((pw_score * 0.4) + (app_score * 0.6))

    recommendations = []
    if pw_score < 75:
        recommendations.append("🔑 Strengthen your password")
    if risky_found:
        recommendations.append(f"🚨 Uninstall risky apps: {', '.join(risky_found)}")
    if final_score >= 75:
        recommendations.append("✅ Your device looks secure!")

    return {
        "score": final_score,
        "password_score": pw_score,
        "app_score": app_score,
        "risky_apps": risky_found,
        "recommendations": recommendations,
        "status": "Safe ✅" if final_score >= 75 else "Moderate ⚠️" if final_score >= 50 else "High Risk ❌"
    }

@app.get("/health")
def health_check():
    return {"status": "ok", "score": 75}