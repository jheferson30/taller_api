import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiEye, FiEyeOff, FiLock, FiClock } from 'react-icons/fi';
import authService from '../services/authService';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [mostrarPassword, setMostrarPassword] = useState(false);
  const [bloqueado, setBloqueado] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const countdownRef = useRef(null);

  useEffect(() => {
    if (countdown > 0) {
      setBloqueado(true);
      countdownRef.current = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            clearInterval(countdownRef.current);
            setBloqueado(false);
            setError('');
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(countdownRef.current);
  }, [countdown]);

  // ── Recuperar contraseña ──
  const [mostrarRecuperar, setMostrarRecuperar] = useState(false);
  const [msgRecuperar, setMsgRecuperar] = useState('');
  const [loadingRecuperar, setLoadingRecuperar] = useState(false);

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await authService.login(username, password);
      navigate('/');
    } catch (err) {
      if (err.retryAfter !== undefined) {
        setCountdown(err.retryAfter || 60);
        setError('');
      } else {
        setError(err.message || 'Error al iniciar sesión');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRecuperar = async (e) => {
    e.preventDefault();
    setLoadingRecuperar(true);
    setMsgRecuperar('');
    try {
      // En producción, usar URL relativa (mismo dominio). En desarrollo, localhost:8000
      const API_BASE = import.meta.env.VITE_API_URL !== undefined 
        ? import.meta.env.VITE_API_URL 
        : (import.meta.env.MODE === 'production' ? '' : 'http://127.0.0.1:8000');
      await fetch(`${API_BASE}/auth/forgot-password-by-username`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username }),
      });
      setMsgRecuperar('✓ Se envió un enlace de recuperación al correo registrado de esta cuenta.');
    } catch {
      setMsgRecuperar('✓ Se envió un enlace de recuperación al correo registrado de esta cuenta.');
    } finally {
      setLoadingRecuperar(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#0A1017' }}>
      <div style={{ background: 'white', padding: '2rem', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', width: '100%', maxWidth: '400px' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <img src="/assets/logo.png" alt="MecaApp" style={{ height: '120px', marginBottom: '1.5rem', filter: 'drop-shadow(0 4px 12px rgba(0, 0, 0, 0.15))' }} />
          <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#333' }}>Iniciar Sesión</h1>
        </div>

        {!mostrarRecuperar ? (
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '1rem' }}>
              <label htmlFor="username" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>Usuario</label>
              <input id="username" type="text" value={username} onChange={(e) => setUsername(e.target.value)}
                required disabled={loading}
                style={{ width: '100%', padding: '0.5rem', border: '1px solid #E2E5EA', borderRadius: '4px', fontSize: '1rem', background: '#F7F8FA' }} />
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label htmlFor="password" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>Contraseña</label>
              <div style={{ position: 'relative' }}>
                <input id="password" type={mostrarPassword ? 'text' : 'password'} value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required disabled={loading}
                  style={{ width: '100%', padding: '0.5rem', paddingRight: '2.5rem', border: '1px solid #E2E5EA', borderRadius: '4px', fontSize: '1rem', boxSizing: 'border-box', background: '#F7F8FA' }} />
                <button type="button" onClick={() => setMostrarPassword(v => !v)}
                  style={{ position: 'absolute', right: '0.5rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#8B95A1', display: 'flex', alignItems: 'center' }}>
                  {mostrarPassword ? <FiEyeOff size={18} /> : <FiEye size={18} />}
                </button>
              </div>
            </div>

            {bloqueado && (
              <div style={{ padding: '0.75rem', marginBottom: '1rem', background: '#450a0a', border: '1px solid #991b1b', borderRadius: '6px', display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                <FiLock size={18} color="#fca5a5" style={{ marginTop: '2px', flexShrink: 0 }} />
                <div>
                  <p style={{ color: '#fca5a5', fontWeight: '700', fontSize: '0.875rem', margin: 0 }}>Acceso bloqueado temporalmente</p>
                  <p style={{ color: '#fecaca', fontSize: '0.8rem', margin: '4px 0 0 0' }}>
                    Demasiados intentos fallidos. Intenta de nuevo en{' '}
                    <span style={{ color: '#f87171', fontWeight: 'bold' }}>{countdown}s</span>
                  </p>
                </div>
              </div>
            )}

            {error && (
              <div style={{ padding: '0.75rem', marginBottom: '0.5rem', background: '#fee', border: '1px solid #fcc', borderRadius: '4px', color: '#c33', fontSize: '0.875rem' }}>
                {error}
              </div>
            )}

            {error && (
              <div style={{ textAlign: 'right', marginBottom: '1rem' }}>
                <button type="button" onClick={() => setMostrarRecuperar(true)}
                  style={{ background: 'none', border: 'none', color: '#D4920A', cursor: 'pointer', fontSize: '0.875rem', textDecoration: 'underline' }}>
                  ¿Olvidaste tu contraseña?
                </button>
              </div>
            )}

            <button type="submit" disabled={loading || bloqueado}
              style={{ width: '100%', padding: '0.75rem', background: (loading || bloqueado) ? '#ccc' : '#D4920A', color: '#0A1017', border: 'none', borderRadius: '4px', fontSize: '1rem', fontWeight: '600', cursor: (loading || bloqueado) ? 'not-allowed' : 'pointer' }}>
              {loading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleRecuperar}>
            <p style={{ marginBottom: '1rem', color: '#555', fontSize: '0.9rem' }}>
              Se enviará un enlace al correo registrado del usuario <strong>{username}</strong>.
            </p>

            {msgRecuperar && (
              <div style={{ padding: '0.75rem', marginBottom: '1rem', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '4px', color: '#166534', fontSize: '0.875rem' }}>
                {msgRecuperar}
              </div>
            )}

            <button type="submit" disabled={loadingRecuperar}
              style={{ width: '100%', padding: '0.75rem', background: loadingRecuperar ? '#ccc' : '#D4920A', color: '#0A1017', border: 'none', borderRadius: '4px', fontSize: '1rem', fontWeight: '600', cursor: loadingRecuperar ? 'not-allowed' : 'pointer', marginBottom: '0.75rem' }}>
              {loadingRecuperar ? 'Enviando...' : 'Enviar enlace al correo registrado'}
            </button>

            <button type="button" onClick={() => { setMostrarRecuperar(false); setMsgRecuperar(''); }}
              style={{ width: '100%', padding: '0.75rem', background: 'none', color: '#0F1923', border: '1px solid #E2E5EA', borderRadius: '4px', fontSize: '1rem', cursor: 'pointer' }}>
              Volver al login
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
