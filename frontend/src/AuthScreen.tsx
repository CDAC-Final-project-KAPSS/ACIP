import React, { useState } from 'react';
import loginBg from './assets/acipbgloginpage.png';
import acipLogo from './assets/aciplogo.png';

export default function AuthScreen({ onLogin, showToast }: { onLogin: (token: string, email: string, role: string) => void, showToast?: (msg: string) => void }) {
  const [mode, setMode] = useState<'LOGIN' | 'SIGNUP_EMAIL' | 'SIGNUP_OTP' | 'SIGNUP_PASSWORD' | 'FORGOT_EMAIL'>('LOGIN');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isForgotPassword, setIsForgotPassword] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (res.ok) {
        onLogin(data.access_token, data.user.email, data.user.role || 'employee');
      } else {
        setError(data.detail || 'Login failed');
      }
    } catch (err) {
      setError('Network error');
    }
  };

  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/auth/request-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      if (res.ok) {
        setIsForgotPassword(false);
        setMode('SIGNUP_OTP');
        if (showToast) showToast('OTP sent successfully');
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to request OTP');
      }
    } catch (err) {
      setError('Network error');
    }
  };

  const handleForgotPasswordOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/auth/forgot-password-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      if (res.ok) {
        setIsForgotPassword(true);
        setMode('SIGNUP_OTP');
        if (showToast) showToast('Password reset OTP sent successfully');
      } else {
        const data = await res.json();
        if (res.status === 404) {
          setError('Account not found. Redirecting to Create Account...');
          setTimeout(() => {
            setMode('SIGNUP_EMAIL');
            setError('');
          }, 1500);
        } else {
          setError(data.detail || 'Failed to request OTP');
        }
      }
    } catch (err) {
      setError('Network error');
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/auth/verify-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, otp })
      });
      if (res.ok) {
        setMode('SIGNUP_PASSWORD');
      } else {
        const data = await res.json();
        setError(data.detail || 'Invalid OTP');
      }
    } catch (err) {
      setError('Network error');
    }
  };

  const handleSetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/auth/set-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      if (res.ok) {
        setMode('LOGIN');
        setPassword('');
        setConfirmPassword('');
        if (showToast) {
          showToast(isForgotPassword ? 'Password updated successfully' : 'Account created successfully');
        }
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to set password');
      }
    } catch (err) {
      setError('Network error');
    }
  };

  return (
    // Applied a unified dark background to the whole wrapper so there are no harsh seams
    <div className="d-flex min-vh-100 flex-column flex-lg-row" style={{ backgroundColor: '#070B16' }}>
      
      {/* Left Side: 60% Image Banner (Hidden on mobile) */}
      <div 
        className="d-none d-lg-block" 
        style={{ 
          flex: '0 0 60%', 
          backgroundImage: `url(${loginBg})`, 
          backgroundSize: 'contain',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
          backgroundColor: '#070B16',
          
        }}
      ></div>

      {/* Right Side: 40% Auth Form */}
      <div className="d-flex align-items-center justify-content-center p-3 p-md-5" style={{ flex: '1 1 40%', backgroundColor: 'transparent' }}>
        
        <div 
          className="glass-card animate-fade-in p-4 p-md-5 w-100 shadow-lg" 
          style={{ 
            maxWidth: '440px', 
            backgroundColor: '#121626', // Solid dark navy block like your screenshot
            borderRadius: '28px', // Fixed the 20% pill-shape to a clean rounded corner
            border: '1px solid rgba(255, 255, 255, 0.05)'
          }}
        >
          <div className="text-center mb-4">
            <div className="mx-auto mb-3 d-flex align-items-center justify-content-center" style={{ width: '96px', height: '96px' }}>
              <img src={acipLogo} alt="ACIP logo" style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain',borderRadius: '10px' }} />
            </div>
            <h2 className="fs-3 fw-bold mb-1 text-light">Autonomous Customs</h2>
            <p className="text-secondary small mb-1">Log in to access intelligence.</p>
            {mode === 'SIGNUP_EMAIL' && (
              <p className="text-primary fw-bold fs-6 mb-2 mt-1">Create Account</p>
            )}
            {mode === 'SIGNUP_OTP' && !isForgotPassword && (
              <p className="text-primary fw-bold fs-6 mb-2 mt-1">Create Account</p>
            )}
            {mode === 'SIGNUP_PASSWORD' && !isForgotPassword && (
              <p className="text-primary fw-bold fs-6 mb-2 mt-1">Create Account</p>
            )}
            {mode === 'FORGOT_EMAIL' && (
              <p className="text-primary fw-bold fs-6 mb-2 mt-1">Forgot Password</p>
            )}
          </div>

          {error && <div className="alert alert-danger py-2 text-center border-0 shadow-sm">{error}</div>}

          {mode === 'LOGIN' && (
            <form onSubmit={handleLogin} className="d-flex flex-column gap-3">
              <div className="form-floating">
                <input className="form-control bg-transparent text-light border-secondary" type="email" id="loginEmail" placeholder="Email Address" value={email} onChange={e => setEmail(e.target.value)} required />
                <label htmlFor="loginEmail" className="text-secondary">Email Address</label>
              </div>
              <div className="position-relative">
                <div className="form-floating">
                  <input 
                    className="form-control bg-transparent text-light border-secondary pe-5" 
                    type={showPassword ? "text" : "password"} 
                    id="loginPassword"
                    placeholder="Password" 
                    value={password} 
                    onChange={e => setPassword(e.target.value)} 
                    required 
                  />
                  <label htmlFor="loginPassword" className="text-secondary">Password</label>
                </div>
                <button 
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="btn btn-link text-secondary position-absolute end-0 top-50 translate-middle-y text-decoration-none border-0"
                  title={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <i className="bi bi-eye-slash fs-5"></i>
                  ) : (
                    <i className="bi bi-eye fs-5"></i>
                  )}
                </button>
              </div>
              <div className="d-flex justify-content-end">
                <span
                  className="text-primary fw-semibold small"
                  style={{ cursor: 'pointer' }}
                  onClick={() => {
                    setIsForgotPassword(true);
                    setMode('FORGOT_EMAIL');
                  }}
                >
                  Forgot Password?
                </span>
              </div>
              <button type="submit" className="btn btn-primary w-100 py-2 mt-3 fw-bold shadow-sm rounded-3">Log In</button>
              <p className="text-center mt-3 text-secondary small">
                Don't have an account? <span className="text-primary fw-semibold" style={{ cursor: 'pointer' }} onClick={() => {
                  setIsForgotPassword(false);
                  setMode('SIGNUP_EMAIL');
                }}>Create Account</span>
              </p>
            </form>
          )}

          {mode === 'FORGOT_EMAIL' && (
            <form onSubmit={handleForgotPasswordOtp} className="d-flex flex-column gap-3">
              <p className="text-secondary text-center small mb-1">Enter your email to receive a password reset OTP.</p>
              <div className="form-floating">
                <input className="form-control bg-transparent text-light border-secondary" type="email" id="forgotEmail" placeholder="Email Address" value={email} onChange={e => setEmail(e.target.value)} required />
                <label htmlFor="forgotEmail" className="text-secondary">Email Address</label>
              </div>
              <button type="submit" className="btn btn-primary w-100 py-2 mt-3 fw-bold shadow-sm rounded-3">Send Reset OTP</button>
              <p className="text-center mt-3 text-secondary small">
                Back to <span className="text-primary fw-semibold" style={{ cursor: 'pointer' }} onClick={() => setMode('LOGIN')}>Login</span>
              </p>
            </form>
          )}

          {mode === 'SIGNUP_EMAIL' && (
            <form onSubmit={handleRequestOtp} className="d-flex flex-column gap-3">
              <p className="text-secondary text-center small mb-1">Enter your email to receive a 6-digit OTP code.</p>
              <div className="form-floating">
                <input className="form-control bg-transparent text-light border-secondary" type="email" id="signupEmail" placeholder="Email Address" value={email} onChange={e => setEmail(e.target.value)} required />
                <label htmlFor="signupEmail" className="text-secondary">Email Address</label>
              </div>
              <button type="submit" className="btn btn-primary w-100 py-2 mt-3 fw-bold shadow-sm rounded-3">Send OTP</button>
              <p className="text-center mt-3 text-secondary small">
                Back to <span className="text-primary fw-semibold" style={{ cursor: 'pointer' }} onClick={() => setMode('LOGIN')}>Login</span>
              </p>
            </form>
          )}

          {mode === 'SIGNUP_OTP' && (
            <form onSubmit={handleVerifyOtp} className="d-flex flex-column gap-3">
              <p className="text-secondary text-center small mb-1">{isForgotPassword ? `We sent a password reset OTP to ${email}.` : `We sent an OTP to ${email}.`}</p>
              <div className="form-floating">
                <input 
                  className="form-control bg-transparent text-light border-secondary text-center fs-4 fw-bold" 
                  type="text" 
                  id="signupOtp" 
                  placeholder="6-digit OTP" 
                  value={otp} 
                  onChange={e => setOtp(e.target.value)} 
                  required 
                  style={{ letterSpacing: '4px' }}
                />
                <label htmlFor="signupOtp" className="text-secondary">6-digit OTP</label>
              </div>
              <button type="submit" className="btn btn-primary w-100 py-2 mt-3 fw-bold shadow-sm rounded-3">Verify OTP</button>
              <p className="text-center mt-3 text-secondary small">
                <span className="text-primary fw-semibold" style={{ cursor: 'pointer' }} onClick={() => setMode('SIGNUP_EMAIL')}>Change Email</span>
              </p>
            </form>
          )}

          {mode === 'SIGNUP_PASSWORD' && (
            <form onSubmit={handleSetPassword} className="d-flex flex-column gap-3">
              <p className="text-secondary text-center small mb-1">{isForgotPassword ? 'Set a new password for your account.' : 'Create a password for your new account.'}</p>
              
              <div className="position-relative">
                <div className="form-floating">
                  <input 
                    className="form-control bg-transparent text-light border-secondary pe-5" 
                    type={showPassword ? "text" : "password"} 
                    id="signupPassword"
                    placeholder="Password" 
                    value={password} 
                    onChange={e => setPassword(e.target.value)} 
                    required 
                  />
                  <label htmlFor="signupPassword" className="text-secondary">Password</label>
                </div>
                <button 
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="btn btn-link text-secondary position-absolute end-0 top-50 translate-middle-y text-decoration-none border-0"
                >
                  {showPassword ? <i className="bi bi-eye-slash fs-5"></i> : <i className="bi bi-eye fs-5"></i>}
                </button>
              </div>

              <div className="form-floating">
                <input 
                  className="form-control bg-transparent text-light border-secondary" 
                  type={showPassword ? "text" : "password"} 
                  id="signupConfirmPassword"
                  placeholder="Confirm Password" 
                  value={confirmPassword} 
                  onChange={e => setConfirmPassword(e.target.value)} 
                  required 
                />
                <label htmlFor="signupConfirmPassword" className="text-secondary">Confirm Password</label>
              </div>

              <button type="submit" className="btn btn-primary w-100 py-2 mt-3 fw-bold shadow-sm rounded-3">Save and Login</button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}