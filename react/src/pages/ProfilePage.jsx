import { useEffect, useState } from 'react';

import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';

const emptyAddress = {
  label: '',
  line1: '',
  line2: '',
  city: '',
  state: '',
  postal_code: '',
  country: 'USA',
  is_default: false,
};

export default function ProfilePage() {
  const { token, user, refreshMe } = useAuth();

  const [profileForm, setProfileForm] = useState({ full_name: user?.full_name || '', phone: user?.phone || '' });
  const [password, setPassword] = useState('');
  const [addresses, setAddresses] = useState([]);
  const [addressForm, setAddressForm] = useState(emptyAddress);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  async function loadAddresses() {
    try {
      const data = await api.addresses.listMine(token);
      setAddresses(data);
    } catch (err) {
      setError(err.message || 'Could not load addresses.');
    }
  }

  useEffect(() => {
    setProfileForm({ full_name: user?.full_name || '', phone: user?.phone || '' });
  }, [user]);

  useEffect(() => {
    loadAddresses();
  }, []);

  async function updateProfile(event) {
    event.preventDefault();
    setError('');
    setMessage('');

    try {
      const payload = {
        full_name: profileForm.full_name,
        phone: profileForm.phone,
      };
      if (password) payload.password = password;

      await api.users.updateMe(token, payload);
      await refreshMe();
      setPassword('');
      setMessage('Profile updated successfully.');
    } catch (err) {
      setError(err.message || 'Profile update failed.');
    }
  }

  async function createAddress(event) {
    event.preventDefault();
    setError('');
    setMessage('');

    try {
      await api.addresses.createMine(token, addressForm);
      setAddressForm(emptyAddress);
      await loadAddresses();
      setMessage('Address added.');
    } catch (err) {
      setError(err.message || 'Address creation failed.');
    }
  }

  async function setDefaultAddress(addressId) {
    try {
      await api.addresses.updateMine(token, addressId, { is_default: true });
      await loadAddresses();
    } catch (err) {
      setError(err.message || 'Could not set default address.');
    }
  }

  async function deleteAddress(addressId) {
    try {
      await api.addresses.deleteMine(token, addressId);
      await loadAddresses();
    } catch (err) {
      setError(err.message || 'Could not delete address.');
    }
  }

  return (
    <section className="section fade-in">
      <div className="section__head">
        <h1>Profile</h1>
        <p className="muted">Manage account details and saved addresses.</p>
      </div>

      {error && <div className="alert alert--error">{error}</div>}
      {message && <div className="alert alert--success">{message}</div>}

      <div className="split-grid">
        <form className="card" onSubmit={updateProfile}>
          <h3>Account Info</h3>

          <label>
            Email
            <input value={user?.email || ''} disabled />
          </label>

          <label>
            Full name
            <input
              value={profileForm.full_name}
              onChange={(event) => setProfileForm((prev) => ({ ...prev, full_name: event.target.value }))}
            />
          </label>

          <label>
            Phone
            <input
              value={profileForm.phone}
              onChange={(event) => setProfileForm((prev) => ({ ...prev, phone: event.target.value }))}
            />
          </label>

          <label>
            New password (optional)
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>

          <button className="btn" type="submit">
            Save profile
          </button>
        </form>

        <div className="stack-gap">
          <form className="card" onSubmit={createAddress}>
            <h3>Add Address</h3>

            <label>
              Label
              <input
                value={addressForm.label}
                onChange={(event) => setAddressForm((prev) => ({ ...prev, label: event.target.value }))}
              />
            </label>

            <label>
              Line 1
              <input
                required
                value={addressForm.line1}
                onChange={(event) => setAddressForm((prev) => ({ ...prev, line1: event.target.value }))}
              />
            </label>

            <label>
              Line 2
              <input
                value={addressForm.line2}
                onChange={(event) => setAddressForm((prev) => ({ ...prev, line2: event.target.value }))}
              />
            </label>

            <div className="grid-two">
              <label>
                City
                <input
                  required
                  value={addressForm.city}
                  onChange={(event) => setAddressForm((prev) => ({ ...prev, city: event.target.value }))}
                />
              </label>
              <label>
                State
                <input
                  required
                  value={addressForm.state}
                  onChange={(event) => setAddressForm((prev) => ({ ...prev, state: event.target.value }))}
                />
              </label>
            </div>

            <div className="grid-two">
              <label>
                Postal code
                <input
                  required
                  value={addressForm.postal_code}
                  onChange={(event) => setAddressForm((prev) => ({ ...prev, postal_code: event.target.value }))}
                />
              </label>
              <label>
                Country
                <input
                  required
                  value={addressForm.country}
                  onChange={(event) => setAddressForm((prev) => ({ ...prev, country: event.target.value }))}
                />
              </label>
            </div>

            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={addressForm.is_default}
                onChange={(event) => setAddressForm((prev) => ({ ...prev, is_default: event.target.checked }))}
              />
              Set as default
            </label>

            <button className="btn btn--ghost" type="submit">
              Add address
            </button>
          </form>

          <div className="card">
            <h3>Saved Addresses</h3>
            {addresses.length === 0 && <p className="muted">No addresses added yet.</p>}

            <ul className="list-clean">
              {addresses.map((address) => (
                <li key={address.id} className="address-item">
                  <p>
                    <strong>{address.label || `Address ${address.id}`}</strong>
                    {address.is_default && <span className="chip">Default</span>}
                  </p>
                  <p className="muted small">
                    {address.line1}, {address.city}, {address.state}, {address.postal_code}, {address.country}
                  </p>
                  <div className="row-gap row-gap--tight">
                    <button type="button" className="btn btn--small" onClick={() => setDefaultAddress(address.id)}>
                      Set default
                    </button>
                    <button
                      type="button"
                      className="btn btn--small btn--danger"
                      onClick={() => deleteAddress(address.id)}
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
