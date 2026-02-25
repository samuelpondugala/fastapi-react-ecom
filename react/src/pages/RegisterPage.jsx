import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register, login } = useAuth();

  const [form, setForm] = useState({
    email: '',
    full_name: '',
    phone: '',
    password: '',
  });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      await register(form);
      await login(form.email, form.password);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.message || 'Registration failed.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="auth-wrap fade-in">
      <form className="card auth-card" onSubmit={onSubmit}>
        <p className="eyebrow">Create account</p>
        <h1>Start shopping and managing</h1>

        {error && <div className="alert alert--error">{error}</div>}

        <label>
          Email
          <input type="email" name="email" value={form.email} onChange={updateField} required />
        </label>

        <label>
          Full name
          <input type="text" name="full_name" value={form.full_name} onChange={updateField} />
        </label>

        <label>
          Phone
          <input type="text" name="phone" value={form.phone} onChange={updateField} />
        </label>

        <label>
          Password
          <input type="password" name="password" value={form.password} onChange={updateField} required />
        </label>

        <button type="submit" className="btn" disabled={submitting}>
          {submitting ? 'Creating account...' : 'Create account'}
        </button>

        <p className="muted small">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </section>
  );
}
