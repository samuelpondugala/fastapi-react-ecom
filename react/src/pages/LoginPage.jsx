import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const redirectTo = location.state?.from?.pathname || '/';

  async function onSubmit(event) {
    event.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      await login(identifier, password);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err.message || 'Login failed.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="auth-wrap fade-in">
      <form className="card auth-card" onSubmit={onSubmit}>
        <p className="eyebrow">Welcome back</p>
        <h1>Sign in to continue</h1>

        {error && <div className="alert alert--error">{error}</div>}

        <label>
          Email or username
          <input
            type="text"
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
            required
          />
        </label>

        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>

        <button type="submit" className="btn" disabled={submitting}>
          {submitting ? 'Signing in...' : 'Sign in'}
        </button>

        <div className="row-gap">
          <button
            type="button"
            className="btn btn--small btn--ghost"
            onClick={() => {
              setIdentifier('ecomadmin');
              setPassword('ecom@123admin');
            }}
          >
            Use demo admin
          </button>
          <button
            type="button"
            className="btn btn--small btn--ghost"
            onClick={() => {
              setIdentifier('ecomvendor');
              setPassword('ecom@123vendor');
            }}
          >
            Use demo vendor
          </button>
        </div>

        <p className="muted small">
          New user? <Link to="/register">Create an account</Link>
        </p>
      </form>
    </section>
  );
}
