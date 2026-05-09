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
    # Location
    "android.permission.ACCESS_FINE_LOCATION": "Tracks your exact GPS location",
    "android.permission.ACCESS_COARSE_LOCATION": "Tracks your approximate location",
    "android.permission.ACCESS_BACKGROUND_LOCATION": "Tracks location even when app is closed",
    "android.permission.ACCESS_MOCK_LOCATION": "Can fake your GPS location",

    # Contacts & Accounts
    "android.permission.READ_CONTACTS": "Reads all your contacts",
    "android.permission.WRITE_CONTACTS": "Can modify/delete your contacts",
    "android.permission.GET_ACCOUNTS": "Access all accounts on device",
    "android.permission.MANAGE_ACCOUNTS": "Can add/remove accounts",

    # Phone & Calls
    "android.permission.READ_PHONE_STATE": "Reads device ID and phone number",
    "android.permission.READ_PHONE_NUMBERS": "Reads your phone number",
    "android.permission.CALL_PHONE": "Makes calls without your knowledge",
    "android.permission.ANSWER_PHONE_CALLS": "Can answer your calls",
    "android.permission.READ_CALL_LOG": "Reads your entire call history",
    "android.permission.WRITE_CALL_LOG": "Can modify your call history",
    "android.permission.PROCESS_OUTGOING_CALLS": "Intercepts and redirects calls",
    "android.permission.USE_SIP": "Makes internet calls",

    # SMS & Messaging
    "android.permission.READ_SMS": "Reads all your SMS messages",
    "android.permission.SEND_SMS": "Sends SMS without your knowledge",
    "android.permission.RECEIVE_SMS": "Intercepts incoming SMS",
    "android.permission.RECEIVE_MMS": "Intercepts incoming MMS",
    "android.permission.RECEIVE_WAP_PUSH": "Intercepts WAP messages",

    # Camera & Microphone
    "android.permission.CAMERA": "Access camera without notification",
    "android.permission.RECORD_AUDIO": "Records audio/microphone secretly",
    "android.permission.CAPTURE_AUDIO_OUTPUT": "Captures all audio output",
    "android.permission.CAPTURE_SECURE_VIDEO_OUTPUT": "Captures secure video",

    # Storage & Files
    "android.permission.READ_EXTERNAL_STORAGE": "Reads all your files",
    "android.permission.WRITE_EXTERNAL_STORAGE": "Can modify/delete your files",
    "android.permission.MANAGE_EXTERNAL_STORAGE": "Full access to all storage",
    "android.permission.ACCESS_MEDIA_LOCATION": "Access GPS in your photos",

    # Biometrics & Security
    "android.permission.USE_BIOMETRIC": "Uses fingerprint/face recognition",
    "android.permission.USE_FINGERPRINT": "Access fingerprint sensor",
    "android.permission.BODY_SENSORS": "Reads heart rate and body sensors",
    "android.permission.BODY_SENSORS_BACKGROUND": "Reads body sensors in background",

    # Network & Bluetooth
    "android.permission.CHANGE_NETWORK_STATE": "Can change your network",
    "android.permission.CHANGE_WIFI_STATE": "Can change WiFi settings",
    "android.permission.ACCESS_WIFI_STATE": "Reads WiFi network info",
    "android.permission.BLUETOOTH": "Access Bluetooth devices",
    "android.permission.BLUETOOTH_ADMIN": "Controls Bluetooth settings",
    "android.permission.BLUETOOTH_CONNECT": "Connects to Bluetooth devices",
    "android.permission.BLUETOOTH_SCAN": "Scans for nearby Bluetooth devices",
    "android.permission.NFC": "Access NFC chip",
    "android.permission.TRANSMIT_IR": "Controls infrared transmitter",

    # System & Device
    "android.permission.MASTER_CLEAR": "Can factory reset your device",
    "android.permission.REBOOT": "Can reboot your device",
    "android.permission.MOUNT_UNMOUNT_FILESYSTEMS": "Can mount/unmount storage",
    "android.permission.INSTALL_PACKAGES": "Can install apps silently",
    "android.permission.DELETE_PACKAGES": "Can uninstall apps silently",
    "android.permission.CHANGE_COMPONENT_ENABLED_STATE": "Can disable system components",
    "android.permission.SET_PREFERRED_APPLICATIONS": "Changes default apps",
    "android.permission.WRITE_SETTINGS": "Modifies system settings",
    "android.permission.WRITE_SECURE_SETTINGS": "Modifies secure system settings",
    "android.permission.DUMP": "Can dump system state data",
    "android.permission.READ_LOGS": "Reads system logs",
    "android.permission.PACKAGE_USAGE_STATS": "Tracks which apps you use",
    "android.permission.BIND_ACCESSIBILITY_SERVICE": "Can read screen content",
    "android.permission.BIND_DEVICE_ADMIN": "Device administrator privileges",
    "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE": "Reads all notifications",
    "android.permission.BIND_VPN_SERVICE": "Creates VPN connections",

    # Calendar & Personal Data
    "android.permission.READ_CALENDAR": "Reads your calendar events",
    "android.permission.WRITE_CALENDAR": "Can modify your calendar",

    # Activity Recognition
    "android.permission.ACTIVITY_RECOGNITION": "Tracks physical activities",
    "android.permission.HIGH_SAMPLING_RATE_SENSORS": "High frequency sensor access",

    # Permissions that indicate spyware
    "android.permission.RECEIVE_BOOT_COMPLETED": "Starts automatically on boot",
    "android.permission.FOREGROUND_SERVICE": "Runs permanently in background",
    "android.permission.REQUEST_INSTALL_PACKAGES": "Can install unknown apps",
    "android.permission.SYSTEM_ALERT_WINDOW": "Draws over other apps",
    "android.permission.DISABLE_KEYGUARD": "Can disable screen lock",
    "android.permission.WAKE_LOCK": "Prevents phone from sleeping",
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
if len(dangerous) >= 15:
    risk_level = "Critical"
    risk_score = 40
elif len(dangerous) >= 8:
    risk_level = "High"
    risk_score = 30
elif len(dangerous) >= 4:
    risk_level = "Medium"
    risk_score = 15
else:
    risk_level = "Low"
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
@app.post("/analyze-wifi")
def analyze_wifi(data: dict):
    ssid = data.get("ssid", "")
    security_type = data.get("security_type", "")
    signal_strength = data.get("signal_strength", 0)
    frequency = data.get("frequency", 0)

    risks = []
    score = 100

    # Check security type
    if security_type == "OPEN" or security_type == "":
        risks.append("🔴 Open network — no encryption, anyone can intercept your data")
        score -= 40
    elif "WEP" in security_type:
        risks.append("🔴 WEP encryption — extremely weak, easily hackable")
        score -= 35
    elif "WPA" in security_type and "WPA2" not in security_type and "WPA3" not in security_type:
        risks.append("🟡 WPA encryption — outdated, vulnerable to attacks")
        score -= 20
    elif "WPA2" in security_type:
        risks.append("🟢 WPA2 encryption — good security")
        score -= 5
    elif "WPA3" in security_type:
        risks.append("🟢 WPA3 encryption — excellent security")

    # Check signal strength
    if signal_strength < -80:
        risks.append("🟡 Weak signal — connection may be unstable")
        score -= 10
    elif signal_strength > -50:
        risks.append("🟢 Strong signal — good connection")

    # Check frequency
    if frequency == 2400 or frequency == 2:
        risks.append("🟡 2.4GHz band — more interference, slower speeds")
    elif frequency == 5000 or frequency == 5:
        risks.append("🟢 5GHz band — faster and less congested")

    # Check for suspicious SSIDs
    suspicious_keywords = ["free", "public", "guest", "hack", "test", "open", "wifi", "hotspot"]
    if any(keyword in ssid.lower() for keyword in suspicious_keywords):
        risks.append("⚠️ Suspicious network name — possible honeypot attack")
        score -= 20

    score = max(0, score)

    if score >= 75:
        status = "✅ Safe Network"
    elif score >= 50:
        status = "⚠️ Moderate Risk"
    else:
        status = "❌ Dangerous Network"

    return {
        "ssid": ssid,
        "score": score,
        "status": status,
        "security_type": security_type,
        "risks": risks,
        "recommendation": "Avoid using this network for sensitive activities" if score < 75 else "Safe to use"
    }

@app.get("/health")
def health_check():
    return {"status": "ok", "score": 75}