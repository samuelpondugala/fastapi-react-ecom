import { Link } from 'react-router-dom';

import { formatMoney } from '../lib/format';

export default function ProductCard({ product, onAddToCart, compact = false }) {
  const primaryImage = product.images?.find((item) => item.is_primary) || product.images?.[0];
  const variant = product.variants?.find((item) => item.is_active) || product.variants?.[0];

  return (
    <article className={`product-card ${compact ? 'product-card--compact' : ''}`}>
      <Link to={`/products/${product.id}`} className="product-card__media">
        {primaryImage ? (
          <img src={primaryImage.image_url} alt={primaryImage.alt_text || product.name} loading="lazy" />
        ) : (
          <div className="image-placeholder">No image</div>
        )}
      </Link>

      <div className="product-card__body">
        <p className="eyebrow">{product.brand || 'Store item'}</p>
        <h3>
          <Link to={`/products/${product.id}`}>{product.name}</Link>
        </h3>
        <p className="muted two-line">{product.description || 'Explore product details and variants.'}</p>

        <div className="product-card__footer">
          <strong>{variant ? formatMoney(variant.price, variant.currency || 'INR') : 'N/A'}</strong>
          <div className="product-card__actions">
            <button
              type="button"
              className="btn btn--small"
              onClick={() => onAddToCart?.(variant)}
              disabled={!variant}
            >
              Add to cart
            </button>
            <Link to="/cart" className="btn btn--small btn--ghost">
              View cart
            </Link>
          </div>
        </div>
      </div>
    </article>
  );
}
