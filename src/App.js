import { useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';

// ── Supabase Auth client ─────────────────────────────────────────────────────
const SUPABASE_URL = 'https://cyshlloaordhtsuktrzj.supabase.co';
const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN5c2hsbG9hb3JkaHRzdWt0cnpqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY1MDUyNjAsImV4cCI6MjEwMjA4MTI2MH0.3xbImQcXi-GjUMN5Y__4Qg5vdUtdLd9kohaxPyuu6Go';
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON);

// ── Backend API ──────────────────────────────────────────────────────────────
const API = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://secureme-backend-h0kx.onrender.com';

export default function App() {
  const [tab, setTab] = useState('home');
  const [user, setUser] = useState(null);
  const [authTab, setAuthTab] = useState('login'); // 'login' | 'register' | 'forgot'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [authError, setAuthError] = useState('');
  const [authSuccess, setAuthSuccess] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [pwInput, setPwInput] = useState('');
  const [pwResult, setPwResult] = useState(null);
  const [pwLoading, setPwLoading] = useState(false);
  const [deviceId, setDeviceId] = useState('');
  const [syncData, setSyncData] = useState(null);
  const [syncLoading, setSyncLoading] = useState(false);
  const [phoneHistory, setPhoneHistory] = useState([]);
  const [phoneId, setPhoneId] = useState('');
  const [fileResult, setFileResult] = useState(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [tipIdx, setTipIdx] = useState(0);

  const tips = [
    { icon: '🔑', title: 'Use Strong Passwords', desc: 'Mix uppercase, numbers and symbols. Never reuse passwords.' },
    { icon: '📱', title: 'Review App Permissions', desc: 'Check which apps have access to your camera, mic and location.' },
    { icon: '🛡️', title: 'Scan Files Regularly', desc: 'Always scan downloaded files before opening them.' },
    { icon: '🔒', title: 'Enable 2FA', desc: 'Two-factor authentication adds an extra layer of security.' },
    { icon: '📶', title: 'Avoid Public WiFi', desc: 'Use VPN when connecting to public networks.' },
  ];

  useEffect(() => {
    // Restore Supabase session on page load
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        const u = session.user;
        setUser({ id: u.id, email: u.email, name: u.user_metadata?.name || '' });
      }
    });
    // Listen for auth state changes (login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        const u = session.user;
        setUser({ id: u.id, email: u.email, name: u.user_metadata?.name || '' });
      } else {
        setUser(null);
      }
    });
    // Restore linked phone ID
    const savedPhoneId = localStorage.getItem('phoneId');
    if (savedPhoneId) { setPhoneId(savedPhoneId); fetchPhoneHistory(savedPhoneId); }
    const interval = setInterval(() => {
      const id = localStorage.getItem('phoneId');
      if (id) fetchPhoneHistory(id);
    }, 30000);
    return () => { subscription.unsubscribe(); clearInterval(interval); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const clearAuthMessages = () => { setAuthError(''); setAuthSuccess(''); };

  const login = async () => {
    setAuthLoading(true); clearAuthMessages();
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) setAuthError(error.message);
    setAuthLoading(false);
  };

  const register = async () => {
    setAuthLoading(true); clearAuthMessages();
    const { error } = await supabase.auth.signUp({
      email, password, options: { data: { name } },
    });
    if (error) {
      setAuthError(error.message);
    } else {
      setAuthTab('verify'); // show email verification screen
      setPassword(''); setName('');
    }
    setAuthLoading(false);
  };

  const resendVerification = async () => {
    setAuthLoading(true); clearAuthMessages();
    const { error } = await supabase.auth.resend({ type: 'signup', email });
    if (error) setAuthError(error.message);
    else setAuthSuccess('📧 Confirmation email resent! Check your inbox.');
    setAuthLoading(false);
  };

  const forgotPassword = async () => {
    setAuthLoading(true); clearAuthMessages();
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: window.location.origin,
    });
    if (error) setAuthError(error.message);
    else setAuthSuccess('📧 Password reset email sent! Check your inbox.');
    setAuthLoading(false);
  };

  const logout = async () => {
    await supabase.auth.signOut();
    localStorage.removeItem('phoneId');
    setPhoneHistory([]); setPhoneId(''); setTab('home'); clearAuthMessages();
  };

  const checkPassword = async () => {
    setPwLoading(true);
    try {
      const res = await fetch(`${API}/check-password`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pwInput })
      });
      setPwResult(await res.json());
    } catch (e) { }
    setPwLoading(false);
  };

  const fetchSync = async () => {
    if (!deviceId) return;
    setSyncLoading(true);
    try {
      const res = await fetch(`${API}/get-scans/${deviceId}`);
      setSyncData(await res.json());
    } catch (e) { }
    setSyncLoading(false);
  };

  const fetchPhoneHistory = async (id) => {
    if (!id) return;
    try {
      const res = await fetch(`${API}/get-scans/${id}`);
      const data = await res.json();
      setPhoneHistory(data.scans || []);
    } catch (e) { }
  };

  const scanFile = async () => {
    if (!selectedFiles.length) return;
    setFileLoading(true); setFileResult(null);
    const results = [];
    for (const file of selectedFiles) {
      try {
        const buffer = await file.arrayBuffer();
        const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        const res = await fetch(`${API}/scan-file`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ file_hash: hash, file_name: file.name })
        });
        const data = await res.json();
        results.push({ ...data, hash, fileName: file.name, size: (file.size / 1024).toFixed(1) });
      } catch (e) {
        results.push({ error: 'Scan failed', fileName: file.name });
      }
    }
    setFileResult(results);
    setFileLoading(false);
  };

  const scoreColor = (s) => s >= 75 ? '#2E7D32' : s >= 50 ? '#B5610A' : '#E53935';

  if (!user) return (
    <div style={{ fontFamily: 'Segoe UI, sans-serif', background: '#F5F5F7', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ background: '#fff', borderRadius: 20, padding: 40, width: 400, boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ fontSize: 40 }}>🛡️</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#1A1A2E' }}>SecureMe</div>
          <div style={{ fontSize: 13, color: '#6B7280' }}>AI-Driven Mobile Security Analyzer</div>
        </div>

        {/* Tab switcher — hidden on Forgot / Verify screens */}
        {authTab !== 'forgot' && authTab !== 'verify' && (
          <div style={{ display: 'flex', marginBottom: 24, background: '#F5F5F7', borderRadius: 10, padding: 4 }}>
            {['login', 'register'].map(t => (
              <button key={t} onClick={() => { setAuthTab(t); clearAuthMessages(); }} style={{
                flex: 1, padding: '8px', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600,
                background: authTab === t ? '#4B4FD9' : 'none', color: authTab === t ? '#fff' : '#6B7280'
              }}>{t === 'login' ? 'Login' : 'Register'}</button>
            ))}
          </div>
        )}

        {/* ── VERIFY EMAIL ── */}
        {authTab === 'verify' && (
          <>
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              <div style={{ fontSize: 56, marginBottom: 12 }}>📬</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#1A1A2E', marginBottom: 8 }}>Check Your Email</div>
              <div style={{ fontSize: 14, color: '#6B7280', lineHeight: 1.6 }}>
                We've sent a confirmation link to:
              </div>
              <div style={{ fontWeight: 700, color: '#4B4FD9', fontSize: 15, margin: '8px 0 16px' }}>{email}</div>
              <div style={{ fontSize: 13, color: '#6B7280', background: '#F9FAFB', borderRadius: 10, padding: 14, textAlign: 'left', lineHeight: 1.7 }}>
                1. Open your email inbox<br />
                2. Click the <strong>"Confirm your email"</strong> link<br />
                3. Come back here and log in ✅
              </div>
            </div>
            {authError && <div style={{ background: '#FEF2F2', color: '#E53935', padding: 10, borderRadius: 8, fontSize: 13, marginBottom: 12 }}>{authError}</div>}
            {authSuccess && <div style={{ background: '#F0FDF4', color: '#2E7D32', padding: 10, borderRadius: 8, fontSize: 13, marginBottom: 12 }}>{authSuccess}</div>}
            <div style={{ fontSize: 12, color: '#9CA3AF', textAlign: 'center', marginBottom: 12 }}>Didn't receive it? Check spam or:</div>
            <button onClick={resendVerification} disabled={authLoading}
              style={{ width: '100%', padding: 12, background: '#4B4FD9', color: '#fff', border: 'none', borderRadius: 10, fontWeight: 700, fontSize: 14, cursor: 'pointer', marginBottom: 10 }}>
              {authLoading ? 'Sending...' : '🔁 Resend Confirmation Email'}
            </button>
            <button onClick={() => { setAuthTab('login'); clearAuthMessages(); }}
              style={{ width: '100%', padding: 10, background: 'none', color: '#4B4FD9', border: '1.5px solid #4B4FD9', borderRadius: 10, fontWeight: 600, fontSize: 14, cursor: 'pointer' }}>
              ← Back to Login
            </button>
          </>
        )}

        {/* ── FORGOT PASSWORD ── */}
        {authTab === 'forgot' && (
          <>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#1A1A2E', marginBottom: 6 }}>🔑 Reset Password</div>
            <div style={{ fontSize: 13, color: '#6B7280', marginBottom: 20 }}>Enter your email and we'll send a reset link via Supabase.</div>
            <div style={{ fontSize: 13, color: '#6B7280', marginBottom: 6 }}>Email</div>
            <input value={email} onChange={e => setEmail(e.target.value)} placeholder="your@email.com" type="email"
              style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1.5px solid #E5E7EB', fontSize: 14, boxSizing: 'border-box', marginBottom: 20 }} />
            {authError && <div style={{ background: '#FEF2F2', color: '#E53935', padding: 10, borderRadius: 8, fontSize: 13, marginBottom: 16 }}>{authError}</div>}
            {authSuccess && <div style={{ background: '#F0FDF4', color: '#2E7D32', padding: 10, borderRadius: 8, fontSize: 13, marginBottom: 16 }}>{authSuccess}</div>}
            <button onClick={forgotPassword} disabled={authLoading} style={{ width: '100%', padding: 12, background: '#4B4FD9', color: '#fff', border: 'none', borderRadius: 10, fontWeight: 700, fontSize: 15, cursor: 'pointer', marginBottom: 12 }}>
              {authLoading ? 'Sending...' : '📧 Send Reset Email'}
            </button>
            <button onClick={() => { setAuthTab('login'); clearAuthMessages(); setEmail(''); }}
              style={{ width: '100%', padding: 10, background: 'none', color: '#4B4FD9', border: '1.5px solid #4B4FD9', borderRadius: 10, fontWeight: 600, fontSize: 14, cursor: 'pointer' }}>
              ← Back to Login
            </button>
          </>
        )}

        {/* ── REGISTER ── */}
        {authTab === 'register' && (
          <>
            <div style={{ fontSize: 13, color: '#6B7280', marginBottom: 6 }}>Full Name</div>
            <input value={name} onChange={e => setName(e.target.value)} placeholder="Your name"
              style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1.5px solid #E5E7EB', fontSize: 14, boxSizing: 'border-box', marginBottom: 14 }} />
            <div style={{ fontSize: 13, color: '#6B7280', marginBottom: 6 }}>Email</div>
            <input value={email} onChange={e => setEmail(e.target.value)} placeholder="your@email.com" type="email"
              style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1.5px solid #E5E7EB', fontSize: 14, boxSizing: 'border-box', marginBottom: 14 }} />
            <div style={{ fontSize: 13, color: '#6B7280', marginBottom: 6 }}>Password</div>
            <input value={password} onChange={e => setPassword(e.target.value)} placeholder="Min 6 characters" type="password"
              style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1.5px solid #E5E7EB', fontSize: 14, boxSizing: 'border-box', marginBottom: 20 }} />
            {authError && <div style={{ background: '#FEF2F2', color: '#E53935', padding: 10, borderRadius: 8, fontSize: 13, marginBottom: 16 }}>{authError}</div>}
            {authSuccess && <div style={{ background: '#F0FDF4', color: '#2E7D32', padding: 10, borderRadius: 8, fontSize: 13, marginBottom: 16 }}>{authSuccess}</div>}
            <button onClick={register} disabled={authLoading} style={{ width: '100%', padding: 12, background: '#4B4FD9', color: '#fff', border: 'none', borderRadius: 10, fontWeight: 700, fontSize: 15, cursor: 'pointer' }}>
              {authLoading ? 'Creating account...' : '📝 Register'}
            </button>
          </>
        )}

        {/* ── LOGIN ── */}
        {authTab === 'login' && (
          <>
            <div style={{ fontSize: 13, color: '#6B7280', marginBottom: 6 }}>Email</div>
            <input value={email} onChange={e => setEmail(e.target.value)} placeholder="your@email.com" type="email"
              style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1.5px solid #E5E7EB', fontSize: 14, boxSizing: 'border-box', marginBottom: 14 }} />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <div style={{ fontSize: 13, color: '#6B7280' }}>Password</div>
              <button onClick={() => { setAuthTab('forgot'); clearAuthMessages(); }}
                style={{ background: 'none', border: 'none', fontSize: 13, color: '#4B4FD9', cursor: 'pointer', padding: 0, fontWeight: 600 }}>
                Forgot password?
              </button>
            </div>
            <input value={password} onChange={e => setPassword(e.target.value)} placeholder="Password" type="password"
              style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1.5px solid #E5E7EB', fontSize: 14, boxSizing: 'border-box', marginBottom: 20 }} />
            {authError && <div style={{ background: '#FEF2F2', color: '#E53935', padding: 10, borderRadius: 8, fontSize: 13, marginBottom: 16 }}>{authError}</div>}
            {authSuccess && <div style={{ background: '#F0FDF4', color: '#2E7D32', padding: 10, borderRadius: 8, fontSize: 13, marginBottom: 16 }}>{authSuccess}</div>}
            <button onClick={login} disabled={authLoading} style={{ width: '100%', padding: 12, background: '#4B4FD9', color: '#fff', border: 'none', borderRadius: 10, fontWeight: 700, fontSize: 15, cursor: 'pointer' }}>
              {authLoading ? 'Please wait...' : '🔐 Login'}
            </button>
          </>
        )}
      </div>
    </div>
  );

  return (
    <div style={{ fontFamily: 'Segoe UI, sans-serif', background: '#F5F5F7', minHeight: '100vh' }}>
      <div style={{ background: '#fff', padding: '12px 24px', display: 'flex', alignItems: 'center', borderBottom: '1px solid #E5E7EB' }}>
        <span style={{ fontSize: 22, marginRight: 8 }}>🛡️</span>
        <span style={{ fontSize: 20, fontWeight: 700, color: '#1A1A2E' }}>SecureMe</span>
        <span style={{ marginLeft: 8, fontSize: 13, color: '#6B7280' }}>AI-Driven Mobile Security Analyzer</span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 13, color: '#6B7280' }}>👤 {user.name || user.email}</span>
          <button onClick={logout} style={{ padding: '6px 14px', background: '#FEF2F2', color: '#E53935', border: '1px solid #FECACA', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>🚪 Logout</button>
        </div>
      </div>

      <div style={{ background: '#fff', display: 'flex', borderBottom: '1px solid #E5E7EB', overflowX: 'auto' }}>
        {[['home', '🏠 Dashboard'], ['password', '🔑 Password'], ['files', '📁 File Scan'], ['sync', '🔄 Sync'], ['about', 'ℹ️ About']].map(([t, label]) => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding: '12px 20px', border: 'none', background: 'none', cursor: 'pointer', whiteSpace: 'nowrap',
            fontWeight: tab === t ? 700 : 400, color: tab === t ? '#4B4FD9' : '#6B7280',
            borderBottom: tab === t ? '2px solid #4B4FD9' : '2px solid transparent', fontSize: 14
          }}>{label}</button>
        ))}
      </div>

      <div style={{ maxWidth: 800, margin: '0 auto', padding: 24 }}>

        {tab === 'home' && <>
          {/* Welcome Card */}
          <div style={{ background: 'linear-gradient(135deg, #4B4FD9, #7B5EA7)', borderRadius: 20, padding: 24, color: '#fff', marginBottom: 20 }}>
            <div style={{ fontSize: 13, opacity: 0.8 }}>Welcome back,</div>
            <div style={{ fontSize: 28, fontWeight: 700, margin: '4px 0' }}>👋 {user.name || user.email.split('@')[0]}</div>
            <div style={{ fontSize: 13, opacity: 0.85, marginBottom: 16 }}>Here's your security overview</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
              <div style={{ background: 'rgba(255,255,255,0.15)', borderRadius: 12, padding: 12, textAlign: 'center' }}>
                <div style={{ fontSize: 22, fontWeight: 700 }}>{phoneHistory.length}</div>
                <div style={{ fontSize: 11, opacity: 0.85 }}>Total Scans</div>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.15)', borderRadius: 12, padding: 12, textAlign: 'center' }}>
                <div style={{ fontSize: 22, fontWeight: 700 }}>{phoneHistory.filter(s => s.score >= 75).length}</div>
                <div style={{ fontSize: 11, opacity: 0.85 }}>Safe Scans</div>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.15)', borderRadius: 12, padding: 12, textAlign: 'center' }}>
                <div style={{ fontSize: 22, fontWeight: 700 }}>{phoneHistory.filter(s => s.score < 75).length}</div>
                <div style={{ fontSize: 11, opacity: 0.85 }}>Risks Found</div>
              </div>
            </div>
          </div>

          {/* Security Tips */}
          <div style={{ background: '#fff', borderRadius: 16, padding: 20, marginBottom: 20, border: '1.5px solid #E5E7EB' }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#1A1A2E', marginBottom: 12 }}>💡 Security Tips</div>
            <div style={{ background: '#EEF2FF', borderRadius: 12, padding: 16, marginBottom: 12 }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>{tips[tipIdx].icon}</div>
              <div style={{ fontWeight: 700, color: '#1A1A2E', marginBottom: 4 }}>{tips[tipIdx].title}</div>
              <div style={{ fontSize: 13, color: '#6B7280' }}>{tips[tipIdx].desc}</div>
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
              {tips.map((_, i) => (
                <div key={i} onClick={() => setTipIdx(i)} style={{ width: i === tipIdx ? 24 : 8, height: 8, borderRadius: 4, background: i === tipIdx ? '#4B4FD9' : '#E5E7EB', cursor: 'pointer' }} />
              ))}
            </div>
          </div>

          {/* Security Overview */}
          <div style={{ fontSize: 18, fontWeight: 700, color: '#1A1A2E', marginBottom: 12 }}>Security Overview</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
            <div style={{ background: '#fff', borderRadius: 12, padding: 16, border: '1.5px solid #E5E7EB' }}>
              <div style={{ fontSize: 24 }}>📱</div>
              <div style={{ fontSize: 12, color: '#6B7280', marginTop: 8 }}>Apps/Safe</div>
              <div style={{ fontWeight: 700 }}>Scan to check</div>
            </div>
            <div style={{ background: '#fff', borderRadius: 12, padding: 16, border: '1.5px solid #B5610A', cursor: 'pointer' }} onClick={() => setTab('password')}>
              <div style={{ fontSize: 24 }}>🔑</div>
              <div style={{ fontSize: 12, color: '#6B7280', marginTop: 8 }}>Password/Check</div>
              <div style={{ fontWeight: 700, color: '#B5610A' }}>Check Now →</div>
            </div>
          </div>
          <div style={{ background: '#fff', borderRadius: 12, padding: 16, border: '1.5px solid #4B4FD9', marginBottom: 12, cursor: 'pointer' }} onClick={() => setTab('files')}>
            <div style={{ fontSize: 24 }}>📁</div>
            <div style={{ fontSize: 12, color: '#6B7280', marginTop: 8 }}>Files/Scan</div>
            <div style={{ fontWeight: 700, color: '#4B4FD9' }}>Scan any file →</div>
          </div>

          {phoneHistory.length > 0 ? (
            <div style={{ marginTop: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#1A1A2E', flex: 1 }}>📱 Phone Scan History</div>
                <button onClick={() => fetchPhoneHistory(phoneId || localStorage.getItem('phoneId'))} style={{ padding: '6px 14px', background: '#4B4FD9', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 13 }}>🔄 Refresh</button>
              </div>
              {phoneHistory.map((scan, i) => {
                const color = scoreColor(scan.score);
                return (
                  <div key={i} style={{ background: '#fff', borderRadius: 12, padding: 16, marginBottom: 8, border: `1.5px solid ${color}50`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: 700, color: '#1A1A2E' }}>{scan.scan_type}</div>
                      <div style={{ fontSize: 12, color: '#6B7280' }}>{scan.created_at.slice(0, 16).replace('T', ' ')}</div>
                      <div style={{ fontSize: 13, color: '#6B7280' }}>{scan.details}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 28, fontWeight: 700, color }}>{scan.score}</div>
                      <div style={{ fontSize: 11, color }}>/100</div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#1A1A2E', marginBottom: 8 }}>📱 Link Your Phone</div>
              <div style={{ display: 'flex', gap: 8 }}>
                <input value={phoneId} onChange={e => setPhoneId(e.target.value)}
                  placeholder="Enter Device ID from SecureMe app → Profile"
                  style={{ flex: 1, padding: '10px 14px', borderRadius: 10, border: '1.5px solid #E5E7EB', fontSize: 13 }} />
                <button onClick={() => { localStorage.setItem('phoneId', phoneId); fetchPhoneHistory(phoneId); }} style={{ padding: '10px 16px', background: '#4B4FD9', color: '#fff', border: 'none', borderRadius: 10, fontWeight: 700, cursor: 'pointer', fontSize: 13 }}>Link</button>
              </div>
            </div>
          )}
        </>}

        {tab === 'files' && (
          <div style={{ background: '#fff', borderRadius: 16, padding: 24 }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#1A1A2E', marginBottom: 4 }}>📁 File Scanner</div>
            <div style={{ fontSize: 14, color: '#6B7280', marginBottom: 24 }}>Upload any file to scan for malware using VirusTotal (74 engines). Works on Windows, Mac, Android!</div>
            <div style={{ border: '2px dashed #E5E7EB', borderRadius: 12, padding: 32, textAlign: 'center', marginBottom: 20, background: '#FAFAFA' }}
              onDragOver={e => e.preventDefault()}
              onDrop={e => { e.preventDefault(); setSelectedFiles(Array.from(e.dataTransfer.files)); setFileResult(null); }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>📂</div>
              <div style={{ fontWeight: 700, color: '#1A1A2E', marginBottom: 8 }}>Drag & drop files here</div>
              <div style={{ color: '#6B7280', fontSize: 13, marginBottom: 16 }}>or click to browse (multiple files supported)</div>
              <input type="file" id="fileInput" multiple style={{ display: 'none' }} onChange={e => { setSelectedFiles(Array.from(e.target.files)); setFileResult(null); }} />
              <label htmlFor="fileInput" style={{ padding: '10px 24px', background: '#4B4FD9', color: '#fff', borderRadius: 10, cursor: 'pointer', fontWeight: 700, fontSize: 14 }}>Browse Files</label>
            </div>
            {selectedFiles.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 13, color: '#6B7280', marginBottom: 8 }}>{selectedFiles.length} file(s) selected:</div>
                {selectedFiles.map((f, i) => (
                  <div key={i} style={{ background: '#EEF2FF', borderRadius: 10, padding: 12, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ fontSize: 20 }}>📄</div>
                    <div>
                      <div style={{ fontWeight: 700, color: '#1A1A2E', fontSize: 14 }}>{f.name}</div>
                      <div style={{ fontSize: 12, color: '#6B7280' }}>{(f.size / 1024).toFixed(1)} KB</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <button onClick={scanFile} disabled={!selectedFiles.length || fileLoading} style={{ width: '100%', padding: 12, background: selectedFiles.length ? '#4B4FD9' : '#E5E7EB', color: selectedFiles.length ? '#fff' : '#9CA3AF', border: 'none', borderRadius: 10, fontWeight: 700, fontSize: 15, cursor: selectedFiles.length ? 'pointer' : 'not-allowed' }}>
              {fileLoading ? `🔍 Scanning ${selectedFiles.length} file(s)...` : '🔍 Scan Files'}
            </button>
            {fileResult && (
              <div style={{ marginTop: 20 }}>
                {fileResult.map((r, i) => r.error ? (
                  <div key={i} style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 10, padding: 16, color: '#E53935', marginBottom: 8 }}>❌ {r.fileName}: {r.error}</div>
                ) : (
                  <div key={i} style={{ background: r.is_malicious ? '#FEF2F2' : '#F0FDF4', border: `1px solid ${r.is_malicious ? '#FECACA' : '#86EFAC'}`, borderRadius: 12, padding: 16, marginBottom: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{ fontSize: 24 }}>{r.is_malicious ? '🚨' : '✅'}</div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 700, color: r.is_malicious ? '#E53935' : '#2E7D32' }}>{r.fileName}</div>
                        <div style={{ fontSize: 12, color: '#6B7280' }}>{r.size} KB • {r.is_malicious ? 'Malware Detected!' : 'File is Clean'}</div>
                        <div style={{ fontSize: 11, fontFamily: 'monospace', color: '#6B7280', marginTop: 4 }}>{r.hash.slice(0, 32)}...</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <div style={{ background: '#EEF2FF', borderRadius: 10, padding: 14, marginTop: 16, fontSize: 13, color: '#4B4FD9' }}>
              💡 SHA-256 hash computed locally — your files are <strong>never uploaded</strong> to our servers.
            </div>
          </div>
        )}

        {tab === 'password' && (
          <div style={{ background: '#fff', borderRadius: 16, padding: 24 }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#1A1A2E', marginBottom: 4 }}>🔑 Password Checker</div>
            <div style={{ fontSize: 14, color: '#6B7280', marginBottom: 24 }}>Verify strength against modern brute-force standards.</div>
            {pwResult && (
              <div style={{ textAlign: 'center', marginBottom: 24 }}>
                <div style={{ width: 120, height: 120, borderRadius: '50%', border: `6px solid ${scoreColor(pwResult.score)}`, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                  <div style={{ fontSize: 32, fontWeight: 700, color: scoreColor(pwResult.score) }}>{pwResult.score}</div>
                  <div style={{ fontSize: 11, color: scoreColor(pwResult.score), letterSpacing: 1 }}>{pwResult.strength.toUpperCase().slice(0, 6)}</div>
                </div>
              </div>
            )}
            <div style={{ marginBottom: 8, fontSize: 13, color: '#6B7280' }}>Enter Password</div>
            <input type="password" value={pwInput} onChange={e => setPwInput(e.target.value)} placeholder="Enter your password"
              style={{ width: '100%', padding: '12px 16px', borderRadius: 10, border: '1.5px solid #E5E7EB', fontSize: 15, boxSizing: 'border-box', marginBottom: 16 }} />
            <button onClick={checkPassword} disabled={pwLoading} style={{ width: '100%', padding: 12, background: '#4B4FD9', color: '#fff', border: 'none', borderRadius: 10, fontWeight: 700, fontSize: 15, cursor: 'pointer' }}>
              {pwLoading ? 'Analyzing...' : '🔍 Analyze Password'}
            </button>
            {pwResult && (
              <div style={{ marginTop: 24 }}>
                <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 12 }}>Security Suggestions</div>
                {pwResult.score >= 75 && <div style={{ background: '#F0FDF4', border: '1px solid #86EFAC', borderRadius: 10, padding: 14, marginBottom: 8, fontSize: 13 }}>✅ Good mix of characters.</div>}
                {pwResult.suggestions.map((s, i) => <div key={i} style={{ background: '#FFFBEB', border: '1px solid #FCD34D', borderRadius: 10, padding: 14, marginBottom: 8, fontSize: 13 }}>⚠️ {s}</div>)}
              </div>
            )}
          </div>
        )}

        {tab === 'sync' && (
          <div style={{ background: '#fff', borderRadius: 16, padding: 24 }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#1A1A2E', marginBottom: 4 }}>🔄 Sync Results</div>
            <div style={{ fontSize: 14, color: '#6B7280', marginBottom: 24 }}>Enter your Android Device ID to see scan results synced from your phone.</div>
            <input value={deviceId} onChange={e => setDeviceId(e.target.value)} placeholder="Find in SecureMe app → Profile → Device ID"
              style={{ width: '100%', padding: '12px 16px', borderRadius: 10, border: '1.5px solid #E5E7EB', fontSize: 14, boxSizing: 'border-box', marginBottom: 16 }} />
            <button onClick={fetchSync} disabled={syncLoading} style={{ width: '100%', padding: 12, background: '#4B4FD9', color: '#fff', border: 'none', borderRadius: 10, fontWeight: 700, fontSize: 15, cursor: 'pointer', marginBottom: 24 }}>
              {syncLoading ? 'Fetching...' : '🔄 Fetch My Scans'}
            </button>
            {syncData && <>
              <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>{syncData.total} scan(s) found</div>
              {(syncData.scans || []).map((scan, i) => (
                <div key={i} style={{ border: `1.5px solid ${scoreColor(scan.score)}30`, borderRadius: 12, padding: 16, marginBottom: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: 700, color: '#1A1A2E' }}>{scan.scan_type}</div>
                      <div style={{ fontSize: 12, color: '#6B7280' }}>{scan.created_at.slice(0, 16).replace('T', ' ')}</div>
                      <div style={{ fontSize: 13, color: '#6B7280', marginTop: 4 }}>{scan.details}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 28, fontWeight: 700, color: scoreColor(scan.score) }}>{scan.score}</div>
                      <div style={{ fontSize: 11, color: scoreColor(scan.score) }}>/100</div>
                    </div>
                  </div>
                </div>
              ))}
            </>}
            <div style={{ background: '#EEF2FF', borderRadius: 10, padding: 14, fontSize: 13, color: '#4B4FD9' }}>
              💡 Find your Device ID: Open SecureMe app → Profile tab
            </div>
          </div>
        )}

        {tab === 'about' && (
          <div style={{ background: '#fff', borderRadius: 16, padding: 24 }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#1A1A2E', marginBottom: 4 }}>ℹ️ About SecureMe</div>
            <div style={{ fontSize: 14, color: '#6B7280', marginBottom: 24 }}>AI-Driven Mobile Security Analyzer</div>
            {[
              ['📁', 'File Scanner', 'Upload any file — SHA-256 + VirusTotal (74 engines)'],
              ['🛡️', 'Permission Analyzer', 'Detects 70+ dangerous permissions across all installed apps'],
              ['🔑', 'Password Checker', 'Real-time strength analysis with improvement suggestions'],
              ['📊', 'Cyber Health Score', 'AI-weighted score (0-100): Safe, Moderate, or High Risk'],
              ['🔋', 'Battery & Performance', 'Monitors RAM usage, temperature, and running processes'],
            ].map(([icon, title, desc], i) => (
              <div key={i} style={{ display: 'flex', gap: 16, padding: '14px 0', borderBottom: '1px solid #F3F4F6' }}>
                <div style={{ fontSize: 28 }}>{icon}</div>
                <div>
                  <div style={{ fontWeight: 700, color: '#1A1A2E' }}>{title}</div>
                  <div style={{ fontSize: 13, color: '#6B7280' }}>{desc}</div>
                </div>
              </div>
            ))}
            <div style={{ marginTop: 20, padding: 16, background: '#4B4FD9', borderRadius: 12, color: '#fff', textAlign: 'center' }}>
              <div style={{ fontWeight: 700, marginBottom: 4 }}>Built with</div>
              <div style={{ fontSize: 13, opacity: 0.9 }}>Kotlin + Jetpack Compose • FastAPI • VirusTotal API • SHA-256</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}