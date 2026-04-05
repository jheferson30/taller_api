import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../services/authService';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

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
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRecuperar = async (e) => {
    e.preventDefault();
    setLoadingRecuperar(true);
    setMsgRecuperar('');
    try {
      const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
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
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
      <div style={{ background: 'white', padding: '2rem', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', width: '100%', maxWidth: '400px' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <img src="/assets/logo.png" alt="PULGA Mecánica Fi" style={{ height: '60px', marginBottom: '1rem' }} />
          <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#333' }}>Iniciar Sesión</h1>
        </div>

        {!mostrarRecuperar ? (
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '1rem' }}>
              <label htmlFor="username" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>Usuario</label>
              <input id="username" type="text" value={username} onChange={(e) => setUsername(e.target.value)}
                required disabled={loading}
                style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px', fontSize: '1rem' }} />
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label htmlFor="password" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>Contraseña</label>
              <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                required disabled={loading}
                style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px', fontSize: '1rem' }} />
            </div>

            {error && (
              <div style={{ padding: '0.75rem', marginBottom: '0.5rem', background: '#fee', border: '1px solid #fcc', borderRadius: '4px', color: '#c33', fontSize: '0.875rem' }}>
                {error}
              </div>
            )}

            {error && (
              <div style={{ textAlign: 'right', marginBottom: '1rem' }}>
                <button type="button" onClick={() => setMostrarRecuperar(true)}
                  style={{ background: 'none', border: 'none', color: '#667eea', cursor: 'pointer', fontSize: '0.875rem', textDecoration: 'underline' }}>
                  ¿Olvidaste tu contraseña?
                </button>
              </div>
            )}

            <button type="submit" disabled={loading}
              style={{ width: '100%', padding: '0.75rem', background: loading ? '#ccc' : '#667eea', color: 'white', border: 'none', borderRadius: '4px', fontSize: '1rem', fontWeight: '500', cursor: loading ? 'not-allowed' : 'pointer' }}>
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
              style={{ width: '100%', padding: '0.75rem', background: loadingRecuperar ? '#ccc' : '#667eea', color: 'white', border: 'none', borderRadius: '4px', fontSize: '1rem', fontWeight: '500', cursor: loadingRecuperar ? 'not-allowed' : 'pointer', marginBottom: '0.75rem' }}>
              {loadingRecuperar ? 'Enviando...' : 'Enviar enlace al correo registrado'}
            </button>

            <button type="button" onClick={() => { setMostrarRecuperar(false); setMsgRecuperar(''); }}
              style={{ width: '100%', padding: '0.75rem', background: 'none', color: '#667eea', border: '1px solid #667eea', borderRadius: '4px', fontSize: '1rem', cursor: 'pointer' }}>
              Volver al login
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
