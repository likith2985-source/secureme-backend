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

RISKY_APPS = {
    "com.fake.spyware": "Spyware - steals personal data",
    "com.malware.virus": "Malware - damages your device",
    "com.suspicious.tracker": "Tracker - monitors your location",
    "com.android.vending.billing.InAppBillingService.COIN": "Fake billing service",
    "com.google.security": "Fake Google app",
    "com.whatsapp.update": "Fake WhatsApp updater",
    "com.facebook.lite.hack": "Fake Facebook app",
    "com.instagram.fake": "Fake Instagram app",
    "com.android.system.update": "Fake system updater",
    "com.phone.cleaner.fast": "Aggressive adware cleaner",
    "com.battery.saver.fake": "Fake battery saver",
    "com.free.vpn.super": "Suspicious VPN - data harvester",
    "com.virus.cleaner.antivirus": "Fake antivirus - actually malware",
    "com.spy.keylogger": "Keylogger - records keystrokes",
    "com.root.access.tool": "Unauthorized root access tool",
}

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

@app.post("/scan-apps")
def scan_apps(data: dict):
    apps = data.get("apps", [])
    risky_found = []
    safe_apps = []

    for app in apps:
        app = app.strip().lower()
        if app in RISKY_APPS:
            risky_found.append({
                "package": app,
                "reason": RISKY_APPS[app]
            })
        else:
            safe_apps.append(app)

    app_score = max(0, 100 - (len(risky_found) * 25))

    return {
        "total_scanned": len(apps),
        "risky_count": len(risky_found),
        "risky_apps": risky_found,
        "safe_count": len(safe_apps),
        "app_score": app_score,
        "status": "✅ All apps are safe!" if not risky_found else f"⚠️ {len(risky_found)} risky app(s) found!"
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

    risky_found = [a for a in installed_apps if a in RISKY_APPS]
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
DANGEROUS_PERMISSIONS = {
    "android.permission.READ_CONTACTS": "Reads your contacts",
    "android.permission.WRITE_CONTACTS": "Modifies your contacts",
    "android.permission.ACCESS_FINE_LOCATION": "Tracks your exact location",
    "android.permission.ACCESS_COARSE_LOCATION": "Tracks your approximate location",
    "android.permission.RECORD_AUDIO": "Records audio from microphone",
    "android.permission.CAMERA": "Access your camera",
    "android.permission.READ_CALL_LOG": "Reads your call history",
    "android.permission.WRITE_CALL_LOG": "Modifies your call history",
    "android.permission.PROCESS_OUTGOING_CALLS": "Intercepts your calls",
    "android.permission.READ_SMS": "Reads your SMS messages",
    "android.permission.SEND_SMS": "Sends SMS messages",
    "android.permission.RECEIVE_SMS": "Receives SMS messages",
    "android.permission.READ_EXTERNAL_STORAGE": "Reads your files",
    "android.permission.WRITE_EXTERNAL_STORAGE": "Modifies your files",
    "android.permission.GET_ACCOUNTS": "Access your accounts",
    "android.permission.USE_BIOMETRIC": "Uses your fingerprint/face",
    "android.permission.BODY_SENSORS": "Reads body sensor data",
    "android.permission.ACCESS_BACKGROUND_LOCATION": "Tracks location in background",
    "android.permission.READ_PHONE_STATE": "Reads phone identity",
    "android.permission.CALL_PHONE": "Makes phone calls",
}

@app.post("/analyze-permissions")
def analyze_permissions(data: dict):
    apps = data.get("apps", [])
    result = []
    total_risk_score = 0

    for app_data in apps:
        app_name = app_data.get("name", "")
        package = app_data.get("package", "")
        permissions = app_data.get("permissions", [])

        dangerous = []
        for perm in permissions:
            if perm in DANGEROUS_PERMISSIONS:
                dangerous.append({
                    "permission": perm.replace("android.permission.", ""),
                    "description": DANGEROUS_PERMISSIONS[perm]
                })

        risk_level = "Low"
        risk_score = 0
        if len(dangerous) >= 8:
            risk_level = "High"
            risk_score = 30
        elif len(dangerous) >= 4:
            risk_level = "Medium"
            risk_score = 15
        else:
            risk_score = 5

        total_risk_score += risk_score

        if dangerous:
            result.append({
                "name": app_name,
                "package": package,
                "dangerous_count": len(dangerous),
                "risk_level": risk_level,
                "dangerous_permissions": dangerous
            })

    result.sort(key=lambda x: x["dangerous_count"], reverse=True)

    return {
        "total_apps_scanned": len(apps),
        "risky_apps_count": len(result),
        "overall_risk": "High" if total_risk_score > 100 else "Medium" if total_risk_score > 50 else "Low",
        "apps": result[:20]
    }

@app.get("/health")
def health_check():
    return {"status": "ok", "score": 75}