import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <section className="section fade-in">
      <div className="card">
        <h1>404</h1>
        <p className="muted">The page you requested does not exist.</p>
        <Link to="/" className="btn btn--small">
          Back to home
        </Link>
      </div>
    </section>
  );
}
