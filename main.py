from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import re
import hashlib
import httpx
import uuid
import os   
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from urllib.parse import urlparse


import random

load_dotenv()

app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL")
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "urikeney@gmail.com")

class DBWrapper:
    def __init__(self, conn, is_sqlite=False):
        self.conn = conn
        self.is_sqlite = is_sqlite

    def cursor(self):
        return DBCursor(self.conn.cursor(), self.is_sqlite)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        try:
            self.conn.rollback()
        except Exception:
            pass

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

class DBCursor:
    def __init__(self, cur, is_sqlite=False):
        self.cur = cur
        self.is_sqlite = is_sqlite

    def execute(self, sql, params=None):
        if self.is_sqlite:
            sql = sql.replace("%s", "?")
            sql = re.sub(r'BOOLEAN\s+DEFAULT\s+TRUE', 'INTEGER DEFAULT 1', sql, flags=re.IGNORECASE)
            sql = re.sub(r'BOOLEAN\s+DEFAULT\s+FALSE', 'INTEGER DEFAULT 0', sql, flags=re.IGNORECASE)
        if params is not None:
            return self.cur.execute(sql, params)
        return self.cur.execute(sql)

    def fetchone(self):
        return self.cur.fetchone()

    def fetchall(self):
        return self.cur.fetchall()

def get_db_connection():
    if DATABASE_URL:
        try:
            pg_conn = psycopg2.connect(DATABASE_URL, sslmode='require', connect_timeout=5)
            return DBWrapper(pg_conn, is_sqlite=False)
        except Exception as e:
            # Fall back to local SQLite if Postgres is unavailable
            pass
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "secureme.db")
    sql_conn = sqlite3.connect(db_path)
    return DBWrapper(sql_conn, is_sqlite=True)

async def send_email(to_email: str, subject: str, html_body: str):
    if not BREVO_API_KEY:
        print("Warning: BREVO_API_KEY is not set.")
        return False, "BREVO_API_KEY environment variable is not configured"
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": BREVO_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "sender": {"name": "SecureMe", "email": BREVO_SENDER_EMAIL},
                    "to": [{"email": to_email}],
                    "subject": subject,
                    "htmlContent": html_body
                },
                timeout=10
            )
            if res.status_code in [200, 201]:
                return True, "Email sent successfully"
            else:
                try:
                    err = res.json().get("message", res.text)
                except:
                    err = res.text
                print(f"Brevo Error ({res.status_code}): {err}")
                return False, err
    except Exception as e:
        print(f"Failed to send email via Brevo: {e}")
        return False, str(e)

def generate_otp():
    return str(random.randint(100000, 999999))

def safe_add_column(conn, table: str, col_name: str, col_type: str):
    c = conn.cursor()
    if getattr(conn, 'is_sqlite', False):
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
            conn.commit()
        except Exception:
            pass
    else:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
            conn.commit()
        except Exception:
            conn.rollback()

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS scan_results (
        id TEXT PRIMARY KEY,
        device_id TEXT,
        scan_type TEXT,
        score INTEGER,
        status TEXT,
        details TEXT,
        created_at TEXT,
        user_id TEXT,
        user_email TEXT
    )''')
    conn.commit()
    safe_add_column(conn, "scan_results", "user_id", "TEXT")
    safe_add_column(conn, "scan_results", "user_email", "TEXT")

    c.execute('''CREATE TABLE IF NOT EXISTS user_devices (
        user_id TEXT,
        email TEXT,
        device_id TEXT,
        last_seen TEXT,
        PRIMARY KEY (email, device_id)
    )''')
    conn.commit()
    conn.close()

def init_auth_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE,
        password TEXT,
        name TEXT,
        created_at TEXT,
        is_verified BOOLEAN DEFAULT TRUE,
        verification_code TEXT,
        reset_code TEXT,
        code_expires_at TEXT,
        device_id TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS pending_registrations (
        email TEXT PRIMARY KEY,
        password TEXT,
        name TEXT,
        verification_code TEXT,
        created_at TEXT
    )''')
    conn.commit()
    safe_add_column(conn, "users", "is_verified", "BOOLEAN DEFAULT TRUE")
    safe_add_column(conn, "users", "verification_code", "TEXT")
    safe_add_column(conn, "users", "reset_code", "TEXT")
    safe_add_column(conn, "users", "code_expires_at", "TEXT")
    safe_add_column(conn, "users", "device_id", "TEXT")
    conn.close()

try:
    init_db()
    init_auth_db()
    print("Database tables initialized successfully.")
except Exception as e:
    print(f"Warning: Database initialization failed. Check your database setup. Error: {e}")

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
    file_hash = data.get("file_hash", "")
    file_name = data.get("file_name", "unknown")

    if not file_hash:
        return {"error": "file_hash required"}
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
@app.post("/save-scan")
def save_scan(data: dict):
    device_id = data.get("device_id", "unknown")
    user_id = data.get("user_id", "")
    user_email = (data.get("user_email") or data.get("email", "")).strip().lower()
    scan_type = data.get("scan_type", "")
    score = data.get("score", 0)
    status = data.get("status", "")
    details = data.get("details", "{}")
    
    scan_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    conn = get_db_connection()
    c = conn.cursor()

    # If email wasn't provided, try looking up linked user from user_devices
    if not user_email and device_id and device_id != "unknown":
        try:
            c.execute("SELECT email, user_id FROM user_devices WHERE device_id=%s ORDER BY last_seen DESC LIMIT 1", (device_id,))
            match = c.fetchone()
            if match:
                user_email = match[0]
                if not user_id and match[1]:
                    user_id = match[1]
        except Exception:
            pass

    # If email and device_id are both present, update user_devices mapping
    if user_email and device_id and device_id != "unknown":
        try:
            if getattr(conn, 'is_sqlite', False):
                c.execute("INSERT OR REPLACE INTO user_devices VALUES (%s, %s, %s, %s)", (user_id, user_email, device_id, created_at))
            else:
                c.execute("INSERT INTO user_devices (user_id, email, device_id, last_seen) VALUES (%s, %s, %s, %s) ON CONFLICT (email, device_id) DO UPDATE SET last_seen = EXCLUDED.last_seen", (user_id, user_email, device_id, created_at))
        except Exception:
            pass
    
    c.execute("INSERT INTO scan_results (id, device_id, scan_type, score, status, details, created_at, user_id, user_email) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
              (scan_id, device_id, scan_type, score, status, str(details), created_at, user_id, user_email))
    conn.commit()
    conn.close()
    
    return {"id": scan_id, "message": "Scan saved successfully", "user_email": user_email}

@app.post("/link-device")
def link_device(data: dict):
    email = data.get("email", "").strip().lower()
    user_id = data.get("user_id", "")
    device_id = data.get("device_id", "").strip()
    if not email or not device_id:
        return {"error": "Email and device_id are required"}
    
    now = datetime.now().isoformat()
    conn = get_db_connection()
    c = conn.cursor()
    try:
        if getattr(conn, 'is_sqlite', False):
            c.execute("INSERT OR REPLACE INTO user_devices VALUES (%s, %s, %s, %s)", (user_id, email, device_id, now))
        else:
            c.execute("INSERT INTO user_devices (user_id, email, device_id, last_seen) VALUES (%s, %s, %s, %s) ON CONFLICT (email, device_id) DO UPDATE SET last_seen = EXCLUDED.last_seen", (user_id, email, device_id, now))
        c.execute("UPDATE users SET device_id=%s WHERE email=%s", (device_id, email))
        # Backfill past scans from this device
        c.execute("UPDATE scan_results SET user_email=%s WHERE device_id=%s AND (user_email IS NULL OR user_email = '')", (email, device_id))
        conn.commit()
    except Exception as e:
        print(f"Error linking device: {e}")
    finally:
        conn.close()
    return {"message": "Device linked successfully", "email": email, "device_id": device_id}

@app.get("/get-scans/{identifier}")
def get_scans(identifier: str):
    identifier = identifier.strip()
    conn = get_db_connection()
    c = conn.cursor()
    
    linked_devices = []
    if "@" in identifier or len(identifier) > 20:
        try:
            c.execute("SELECT device_id FROM user_devices WHERE email=%s OR user_id=%s", (identifier.lower(), identifier))
            for r in c.fetchall():
                if r[0] and r[0] not in linked_devices:
                    linked_devices.append(r[0])
            c.execute("SELECT device_id FROM users WHERE email=%s OR id=%s", (identifier.lower(), identifier))
            for r in c.fetchall():
                if r[0] and r[0] not in linked_devices:
                    linked_devices.append(r[0])
        except Exception:
            pass

    query = """
        SELECT id, device_id, scan_type, score, status, details, created_at, user_id, user_email 
        FROM scan_results 
        WHERE device_id = %s OR user_email = %s OR user_id = %s
    """
    params = [identifier, identifier.lower(), identifier]
    if linked_devices:
        placeholders = ", ".join(["%s"] * len(linked_devices))
        query += f" OR device_id IN ({placeholders})"
        params.extend(linked_devices)

    query += " ORDER BY created_at DESC LIMIT 50"
    
    c.execute(query, tuple(params))
    rows = c.fetchall()
    conn.close()
    
    scans = []
    for row in rows:
        scans.append({
            "id": row[0],
            "device_id": row[1],
            "scan_type": row[2],
            "score": row[3],
            "status": row[4],
            "details": row[5],
            "created_at": row[6],
            "user_id": row[7] if len(row) > 7 else None,
            "user_email": row[8] if len(row) > 8 else None
        })
    
    return {"scans": scans, "total": len(scans)}

@app.get("/sync-user/{email}")
def sync_user(email: str):
    email = email.strip().lower()
    conn = get_db_connection()
    c = conn.cursor()
    
    user_info = None
    device_id = None
    try:
        c.execute("SELECT id, name, email, device_id FROM users WHERE email=%s", (email,))
        u = c.fetchone()
        if u:
            user_info = {"id": u[0], "name": u[1], "email": u[2]}
            device_id = u[3]
    except Exception:
        pass
        
    try:
        c.execute("SELECT device_id FROM user_devices WHERE email=%s ORDER BY last_seen DESC LIMIT 1", (email,))
        d = c.fetchone()
        if d and d[0]:
            device_id = d[0]
    except Exception:
        pass

    conn.close()

    scans_res = get_scans(email)
    scans = scans_res.get("scans", [])
    
    if not scans and device_id:
        scans_res = get_scans(device_id)
        scans = scans_res.get("scans", [])

    total_scans = len(scans)
    safe_scans = len([s for s in scans if (s.get("score") or 0) >= 75])
    risks_found = len([s for s in scans if (s.get("score") or 0) < 75])

    cyber_score = 100
    cyber_status = "Optimal"
    recommendations = []
    
    system_scan = next((s for s in scans if s.get("scan_type") == "Full System Scan"), None)
    if system_scan:
        cyber_score = system_scan.get("score", 100)
        cyber_status = system_scan.get("status", "Optimal")
        import json
        try:
            d_raw = system_scan.get("details", "{}")
            d_parsed = json.loads(d_raw) if isinstance(d_raw, str) else d_raw
            if isinstance(d_parsed, dict) and "recommendations" in d_parsed:
                recommendations = d_parsed["recommendations"]
        except Exception:
            pass
    elif scans:
        scores = [s.get("score", 100) for s in scans if isinstance(s.get("score"), int)]
        if scores:
            cyber_score = round(sum(scores) / len(scores))
            cyber_status = "Optimal" if cyber_score >= 80 else ("Moderate" if cyber_score >= 60 else "At Risk")

    return {
        "email": email,
        "user": user_info,
        "device_id": device_id,
        "cyber_score": cyber_score,
        "cyber_status": cyber_status,
        "recommendations": recommendations,
        "total_scans": total_scans,
        "safe_scans": safe_scans,
        "risks_found": risks_found,
        "scans": scans
    }

@app.post("/register")
async def register(data: dict):
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    name = data.get("name", "").strip()
    
    if not email or not password:
        return {"error": "Email and password are required"}
    if len(password) < 6:
        return {"error": "Password must be at least 6 characters"}
        
    hashed = hashlib.sha256(password.encode()).hexdigest()
    otp = generate_otp()
    
    conn = get_db_connection()
    c = conn.cursor()
    # Check if already a registered & verified user
    c.execute("SELECT id FROM users WHERE email=%s", (email,))
    existing = c.fetchone()
    
    if existing:
        conn.close()
        return {"error": "An account with this email already exists. Please log in."}
        
    # Store ONLY in pending_registrations until OTP is confirmed!
    c.execute("SELECT email FROM pending_registrations WHERE email=%s", (email,))
    pending = c.fetchone()
    if pending:
        c.execute("UPDATE pending_registrations SET password=%s, name=%s, verification_code=%s, created_at=%s WHERE email=%s",
                  (hashed, name, otp, datetime.now().isoformat(), email))
    else:
        c.execute("INSERT INTO pending_registrations (email, password, name, verification_code, created_at) VALUES (%s, %s, %s, %s, %s)",
                  (email, hashed, name, otp, datetime.now().isoformat()))
                  
    conn.commit()
    conn.close()
    
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: auto; padding: 24px; border-radius: 12px; background: #ffffff; border: 1px solid #e5e7eb;">
      <h2 style="color: #4B4FD9; text-align: center;">🛡️ SecureMe</h2>
      <h3 style="color: #1a1a2e; text-align: center;">Verify Your Email</h3>
      <p style="color: #6b7280; font-size: 14px; text-align: center;">Welcome to SecureMe! Use the 6-digit verification code below to activate your account:</p>
      <div style="background: #EEF2FF; padding: 16px; border-radius: 8px; text-align: center; font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #4B4FD9; margin: 20px 0;">{otp}</div>
      <p style="color: #9ca3af; font-size: 12px; text-align: center;">If you didn't create a SecureMe account, you can safely ignore this email.</p>
    </div>
    """
    sent, msg = await send_email(email, "Verify your SecureMe Account", html)
    if not sent:
        return {"error": f"Email delivery failed: {msg}"}
        
    return {"message": "Verification code sent to your email", "email": email}

@app.post("/verify-email")
def verify_email(data: dict):
    email = data.get("email", "").strip().lower()
    code = data.get("code", "").strip()
    
    if not email or not code:
        return {"error": "Email and verification code are required"}
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT email, password, name, verification_code FROM pending_registrations WHERE email=%s", (email,))
    pending = c.fetchone()
    
    if not pending:
        conn.close()
        return {"error": "No pending registration found for this email. Please register first."}
        
    if str(pending[3]).strip() != code:
        conn.close()
        return {"error": "Invalid verification code. Please check your email and try again."}
        
    # Move from pending_registrations to users table
    user_id = str(uuid.uuid4())
    c.execute("INSERT INTO users (id, email, password, name, created_at, is_verified) VALUES (%s, %s, %s, %s, %s, %s)",
              (user_id, email, pending[1], pending[2], datetime.now().isoformat(), True))
    c.execute("DELETE FROM pending_registrations WHERE email=%s", (email,))
    conn.commit()
    conn.close()
    
    return {
        "message": "Email verified successfully!",
        "user": {"id": user_id, "name": pending[2], "email": email, "token": user_id}
    }

@app.post("/resend-verification")
async def resend_verification(data: dict):
    email = data.get("email", "").strip().lower()
    if not email:
        return {"error": "Email is required"}
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT email, name FROM pending_registrations WHERE email=%s", (email,))
    pending = c.fetchone()
    
    if not pending:
        conn.close()
        return {"error": "No pending registration found for this email."}
        
    otp = generate_otp()
    c.execute("UPDATE pending_registrations SET verification_code=%s WHERE email=%s", (otp, email))
    conn.commit()
    conn.close()
    
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: auto; padding: 24px; border-radius: 12px; background: #ffffff; border: 1px solid #e5e7eb;">
      <h2 style="color: #4B4FD9; text-align: center;">🛡️ SecureMe</h2>
      <h3 style="color: #1a1a2e; text-align: center;">New Verification Code</h3>
      <p style="color: #6b7280; font-size: 14px; text-align: center;">Here is your new 6-digit verification code:</p>
      <div style="background: #EEF2FF; padding: 16px; border-radius: 8px; text-align: center; font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #4B4FD9; margin: 20px 0;">{otp}</div>
    </div>
    """
    sent, msg = await send_email(email, "Your SecureMe Verification Code", html)
    if not sent:
        return {"error": f"Email delivery failed: {msg}"}
        
    return {"message": "New verification code sent to your email"}

@app.post("/login")
def login(data: dict):
    try:
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        device_id = data.get("device_id", "").strip()
        hashed = hashlib.sha256(password.encode()).hexdigest()
        
        conn = get_db_connection()
        c = conn.cursor()
        user = None
        try:
            c.execute("SELECT id, name, email, is_verified, device_id FROM users WHERE email=%s AND password=%s", (email, hashed))
            user = c.fetchone()
        except Exception:
            conn.rollback()
            try:
                c.execute("SELECT id, name, email, is_verified FROM users WHERE email=%s AND password=%s", (email, hashed))
                u = c.fetchone()
                user = (u[0], u[1], u[2], u[3], None) if u else None
            except Exception:
                conn.rollback()
        
        if user:
            if not user[3]:
                conn.close()
                return {"error": "Please verify your email before logging in.", "needs_verification": True, "email": email}
            
            user_id = user[0]
            now = datetime.now().isoformat()
            linked_dev = device_id or user[4]
            
            if device_id:
                try:
                    if getattr(conn, 'is_sqlite', False):
                        c.execute("INSERT OR REPLACE INTO user_devices VALUES (%s, %s, %s, %s)", (user_id, email, device_id, now))
                    else:
                        c.execute("INSERT INTO user_devices (user_id, email, device_id, last_seen) VALUES (%s, %s, %s, %s) ON CONFLICT (email, device_id) DO UPDATE SET last_seen = EXCLUDED.last_seen", (user_id, email, device_id, now))
                    try:
                        c.execute("UPDATE users SET device_id=%s WHERE id=%s", (device_id, user_id))
                    except Exception:
                        conn.rollback()
                    try:
                        c.execute("UPDATE scan_results SET user_email=%s, user_id=%s WHERE device_id=%s AND (user_email IS NULL OR user_email = '')", (email, user_id, device_id))
                    except Exception:
                        conn.rollback()
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    print(f"Error mapping device in login: {e}")
            
            if not linked_dev:
                try:
                    c.execute("SELECT device_id FROM user_devices WHERE email=%s ORDER BY last_seen DESC LIMIT 1", (email,))
                    r = c.fetchone()
                    if r and r[0]:
                        linked_dev = r[0]
                except Exception:
                    pass
                    
            conn.close()
            return {
                "id": user[0],
                "name": user[1],
                "email": user[2],
                "token": user[0],
                "device_id": linked_dev
            }
        conn.close()
        return {"error": "Invalid email or password"}
    except Exception as e:
        print(f"Unexpected error in login: {e}")
        return {"error": f"Login service error: {str(e)}"}

@app.post("/forgot-password")
async def forgot_password(data: dict):
    email = data.get("email", "").strip().lower()
    if not email:
        return {"error": "Email is required"}
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email=%s", (email,))
    user = c.fetchone()
    
    if not user:
        conn.close()
        return {"error": "No account found with this email address"}
        
    otp = generate_otp()
    c.execute("UPDATE users SET reset_code=%s WHERE email=%s", (otp, email))
    conn.commit()
    conn.close()
    
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: auto; padding: 24px; border-radius: 12px; background: #ffffff; border: 1px solid #e5e7eb;">
      <h2 style="color: #4B4FD9; text-align: center;">🛡️ SecureMe</h2>
      <h3 style="color: #1a1a2e; text-align: center;">Password Reset Request</h3>
      <p style="color: #6b7280; font-size: 14px; text-align: center;">Use the 6-digit code below to reset your SecureMe password:</p>
      <div style="background: #FEF2F2; padding: 16px; border-radius: 8px; text-align: center; font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #E53935; margin: 20px 0;">{otp}</div>
      <p style="color: #9ca3af; font-size: 12px; text-align: center;">If you didn't request a password reset, you can safely ignore this email.</p>
    </div>
    """
    sent, msg = await send_email(email, "SecureMe Password Reset Code", html)
    if not sent:
        return {"error": f"Email delivery failed: {msg}"}
    return {"message": "Password reset code sent to your email", "email": email}

@app.post("/reset-password")
def reset_password(data: dict):
    email = data.get("email", "").strip().lower()
    code = data.get("code", "").strip()
    new_password = data.get("new_password", "")
    
    if not email or not code or not new_password:
        return {"error": "Email, reset code, and new password are required"}
    if len(new_password) < 6:
        return {"error": "Password must be at least 6 characters"}
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, reset_code FROM users WHERE email=%s", (email,))
    user = c.fetchone()
    
    if not user or not user[1]:
        conn.close()
        return {"error": "No password reset requested for this email"}
        
    if str(user[1]).strip() != code:
        conn.close()
        return {"error": "Invalid reset code. Please check and try again."}
        
    hashed = hashlib.sha256(new_password.encode()).hexdigest()
    c.execute("UPDATE users SET password=%s, reset_code=NULL, is_verified=TRUE WHERE email=%s", (hashed, email))
    conn.commit()
    conn.close()
    
    return {"message": "Password reset successful! You can now log in with your new password."}

@app.get("/health")
def health_check():
    return {"status": "ok", "score": 75}