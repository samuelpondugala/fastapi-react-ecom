import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import { formatDate, formatMoney } from '../lib/format';

export default function ProductPage() {
  const { token } = useAuth();
  const { productId } = useParams();

  const [product, setProduct] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [selectedVariantId, setSelectedVariantId] = useState('');
  const [selectedImageId, setSelectedImageId] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [reviewForm, setReviewForm] = useState({ rating: 5, title: '', comment: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let ignore = false;

    async function load() {
      setLoading(true);
      setError('');
      try {
        const [productData, reviewData] = await Promise.all([
          api.products.getById(productId),
          api.reviews.listByProduct(productId),
        ]);

        if (ignore) return;
        setProduct(productData);
        setReviews(reviewData);

        const activeVariant = productData.variants?.find((item) => item.is_active) || productData.variants?.[0];
        setSelectedVariantId(activeVariant ? String(activeVariant.id) : '');
        const primaryImage = productData.images?.find((item) => item.is_primary) || productData.images?.[0];
        setSelectedImageId(primaryImage ? String(primaryImage.id) : '');
      } catch (err) {
        if (!ignore) setError(err.message || 'Failed to load product details.');
      } finally {
        if (!ignore) setLoading(false);
      }
    }

    load();
    return () => {
      ignore = true;
    };
  }, [productId]);

  useEffect(() => {
    if (!success) return undefined;
    const timeout = window.setTimeout(() => setSuccess(''), 2500);
    return () => window.clearTimeout(timeout);
  }, [success]);

  const selectedVariant = useMemo(
    () => product?.variants?.find((item) => String(item.id) === String(selectedVariantId)),
    [product, selectedVariantId],
  );

  const orderedImages = useMemo(() => {
    const images = [...(product?.images || [])];
    images.sort((a, b) => {
      if (a.is_primary !== b.is_primary) return a.is_primary ? -1 : 1;
      if ((a.sort_order || 0) !== (b.sort_order || 0)) return (a.sort_order || 0) - (b.sort_order || 0);
      return a.id - b.id;
    });
    return images;
  }, [product]);

  const selectedImage = useMemo(
    () => orderedImages.find((item) => String(item.id) === String(selectedImageId)) || orderedImages[0] || null,
    [orderedImages, selectedImageId],
  );

  const variantAttributes = useMemo(() => {
    if (!selectedVariant || !selectedVariant.attributes_json || typeof selectedVariant.attributes_json !== 'object') {
      return [];
    }
    return Object.entries(selectedVariant.attributes_json).filter(
      ([, value]) => value !== '' && value !== null && value !== undefined,
    );
  }, [selectedVariant]);

  async function handleAddToCart() {
    if (!token) {
      setError('Please login to add this item to cart.');
      setSuccess('');
      return;
    }

    if (!selectedVariant) {
      setError('Please choose a valid variant.');
      setSuccess('');
      return;
    }

    try {
      await api.cart.addItem(token, { variant_id: selectedVariant.id, quantity });
      setError('');
      setSuccess('Item added to cart.');
    } catch (err) {
      setSuccess('');
      setError(err.message || 'Could not add to cart.');
    }
  }

  async function submitReview(event) {
    event.preventDefault();
    if (!token) {
      setError('Please login to submit a review.');
      return;
    }

    try {
      await api.reviews.create(token, {
        product_id: Number(productId),
        rating: Number(reviewForm.rating),
        title: reviewForm.title,
        comment: reviewForm.comment,
      });
      const reviewData = await api.reviews.listByProduct(productId);
      setReviews(reviewData);
      setReviewForm({ rating: 5, title: '', comment: '' });
      setError('');
      setSuccess('Review submitted successfully.');
    } catch (err) {
      setSuccess('');
      setError(err.message || 'Review submit failed.');
    }
  }

  if (loading) {
    return (
      <div className="centered-screen">
        <div className="loader" />
        <p>Loading product...</p>
      </div>
    );
  }

  if (!product) {
    return <div className="alert alert--error">Product not found.</div>;
  }

  return (
    <section className="section fade-in">
      {error && <div className="alert alert--error">{error}</div>}
      {success && <div className="alert alert--success">{success}</div>}

      <div className="product-detail card">
        <div className="product-detail__media">
          <div className="product-gallery">
            <div className="product-gallery__main">
              {selectedImage ? (
                <img src={selectedImage.image_url} alt={selectedImage.alt_text || product.name} />
              ) : (
                <div className="image-placeholder">No image</div>
              )}
            </div>
            {orderedImages.length > 1 && (
              <div className="product-gallery__thumbs" role="listbox" aria-label="Product images">
                {orderedImages.map((image) => (
                  <button
                    key={image.id}
                    type="button"
                    className={`product-gallery__thumb ${
                      String(image.id) === String(selectedImage?.id) ? 'product-gallery__thumb--active' : ''
                    }`}
                    aria-label={`View image ${image.id}`}
                    onClick={() => setSelectedImageId(String(image.id))}
                  >
                    <img src={image.image_url} alt={image.alt_text || product.name} loading="lazy" />
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="product-detail__content">
          <p className="eyebrow">{product.brand || 'Catalog item'}</p>
          <h1>{product.name}</h1>
          <p className="muted">{product.description || 'No description available.'}</p>
          <p className="product-price">
            {selectedVariant ? formatMoney(selectedVariant.price, selectedVariant.currency || 'USD') : 'N/A'}
          </p>

          <label>
            Variant
            <select
              value={selectedVariantId}
              onChange={(event) => setSelectedVariantId(event.target.value)}
              className="full-width"
            >
              {product.variants?.map((variant) => (
                <option key={variant.id} value={variant.id}>
                  {variant.sku} | {formatMoney(variant.price, variant.currency || 'USD')}
                </option>
              ))}
            </select>
          </label>

          {variantAttributes.length > 0 && (
            <div className="variant-specs">
              {variantAttributes.map(([key, value]) => (
                <p key={key}>
                  <span>{key}</span>
                  <strong>{String(value)}</strong>
                </p>
              ))}
            </div>
          )}

          <label>
            Quantity
            <input
              type="number"
              min="1"
              max="100"
              value={quantity}
              onChange={(event) => setQuantity(Number(event.target.value) || 1)}
            />
          </label>

          <div className="row-gap">
            <button className="btn" onClick={handleAddToCart} type="button">
              Add to cart
            </button>
            <Link className="btn btn--ghost" to="/cart">
              View cart
            </Link>
          </div>
        </div>
      </div>

      <div className="section__head">
        <h2>Reviews</h2>
      </div>

      <div className="split-grid">
        <div className="card">
          <h3>Customer Feedback</h3>
          {reviews.length === 0 && <p className="muted">No reviews yet.</p>}
          {reviews.map((review) => (
            <article key={review.id} className="review-item">
              <p>
                <strong>{review.rating}/5</strong> {review.title ? `- ${review.title}` : ''}
              </p>
              <p className="muted">{review.comment || 'No comment provided.'}</p>
              <p className="small muted">
                {review.is_verified_purchase ? 'Verified purchase' : 'Unverified'} • {formatDate(review.created_at)}
              </p>
            </article>
          ))}
        </div>

        <form className="card" onSubmit={submitReview}>
          <h3>Write a review</h3>

          <label>
            Rating
            <select
              value={reviewForm.rating}
              onChange={(event) => setReviewForm((prev) => ({ ...prev, rating: Number(event.target.value) }))}
            >
              <option value={5}>5</option>
              <option value={4}>4</option>
              <option value={3}>3</option>
              <option value={2}>2</option>
              <option value={1}>1</option>
            </select>
          </label>

          <label>
            Title
            <input
              type="text"
              value={reviewForm.title}
              onChange={(event) => setReviewForm((prev) => ({ ...prev, title: event.target.value }))}
            />
          </label>

          <label>
            Comment
            <textarea
              rows="5"
              value={reviewForm.comment}
              onChange={(event) => setReviewForm((prev) => ({ ...prev, comment: event.target.value }))}
            />
          </label>

          <button className="btn" type="submit">
            Submit review
          </button>
        </form>
      </div>
    </section>
  );
}
