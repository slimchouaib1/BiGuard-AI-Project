import React, { useState } from 'react';
import { PlaidLink } from 'react-plaid-link';

const Signup = () => {
  const [form, setForm] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
    confirmPassword: '',
    agreeToTerms: false,
    subscribeNewsletter: false
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [linkToken, setLinkToken] = useState(null);
  const [showPlaid, setShowPlaid] = useState(false);

  const handleChange = e => {
    const { name, value, type, checked } = e.target;
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleSubmit = async e => {
    e.preventDefault();
    setError('');
    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (!form.agreeToTerms) {
      setError('You must agree to the terms');
      return;
    }
    setLoading(true);
    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          first_name: form.firstName,
          last_name: form.lastName,
          email: form.email,
          password: form.password
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Registration failed');
      // Store access token for Plaid API calls
      localStorage.setItem('access_token', data.access_token);
      // Get Plaid link token
      const plaidRes = await fetch('/api/plaid/create-link-token', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${data.access_token}` }
      });
      const plaidData = await plaidRes.json();
      if (!plaidRes.ok || !plaidData.link_token) throw new Error('Could not create Plaid link token');
      setLinkToken(plaidData.link_token);
      setShowPlaid(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Plaid Link success handler
  const handlePlaidSuccess = async (publicToken) => {
    const token = localStorage.getItem('access_token');
    try {
      const response = await fetch('/api/plaid/exchange-token', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ public_token: publicToken, remember_account: true })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Plaid token exchange failed');
      // Redirect to dashboard after successful linking
      window.location.href = '/dashboard';
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="w-full border-b bg-white">
        <div className="container mx-auto flex h-16 items-center justify-between px-4 md:px-6">
          <a href="/" className="flex items-center space-x-2">
            <svg className="h-8 w-8 text-biguard-orange" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            <span className="text-2xl font-bold text-biguard-gray">BiGuard</span>
          </a>
          <a href="/" className="flex items-center space-x-2 text-biguard-gray hover:text-biguard-orange transition-colors">
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            <span>Back to Home</span>
          </a>
        </div>
      </header>
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-white rounded-lg shadow-lg p-6">
          <div className="text-center mb-6">
            <h1 className="text-2xl font-bold text-biguard-gray">Create Your Account</h1>
            <p className="text-gray-600 mt-2">Join thousands of users who trust BiGuard with their financial security</p>
          </div>
          {/* Show Plaid Link after signup, otherwise show signup form */}
          {showPlaid && linkToken ? (
            <div className="flex flex-col items-center justify-center">
              <h2 className="text-xl font-semibold mb-4">Link your bank account to get started</h2>
              <PlaidLink
                token={linkToken}
                onSuccess={handlePlaidSuccess}
                className="bg-biguard-orange text-white px-6 py-3 rounded-lg font-semibold shadow hover:bg-orange-600 transition-colors text-lg flex items-center gap-2"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                Link Bank Account
              </PlaidLink>
              <div className="mt-4 text-gray-500 text-sm">You must link a bank account to use BiGuard.</div>
              {error && <div className="text-red-500 text-sm mt-2">{error}</div>}
            </div>
          ) : (
            <>
              <form className="space-y-4" onSubmit={handleSubmit}>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="firstName" className="block text-sm font-medium text-gray-700 mb-1">First Name</label>
                    <input type="text" id="firstName" name="firstName" required value={form.firstName} onChange={handleChange} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-biguard-orange focus:border-transparent" />
                  </div>
                  <div>
                    <label htmlFor="lastName" className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
                    <input type="text" id="lastName" name="lastName" required value={form.lastName} onChange={handleChange} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-biguard-orange focus:border-transparent" />
                  </div>
                </div>
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">Email Address</label>
                  <input type="email" id="email" name="email" required value={form.email} onChange={handleChange} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-biguard-orange focus:border-transparent" />
                </div>
                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                  <input type="password" id="password" name="password" required value={form.password} onChange={handleChange} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-biguard-orange focus:border-transparent" />
                </div>
                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">Confirm Password</label>
                  <input type="password" id="confirmPassword" name="confirmPassword" required value={form.confirmPassword} onChange={handleChange} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-biguard-orange focus:border-transparent" />
                </div>
                <div className="space-y-3">
                  <div className="flex items-center">
                    <input type="checkbox" id="agreeToTerms" name="agreeToTerms" checked={form.agreeToTerms} onChange={handleChange} className="h-4 w-4 text-biguard-orange focus:ring-biguard-orange border-gray-300 rounded" />
                    <label htmlFor="agreeToTerms" className="ml-2 block text-sm text-gray-700">
                      I agree to the <a href="#" className="text-biguard-orange hover:underline">Terms of Service</a> and <a href="#" className="text-biguard-orange hover:underline">Privacy Policy</a>
                    </label>
                  </div>
                  <div className="flex items-center">
                    <input type="checkbox" id="subscribeNewsletter" name="subscribeNewsletter" checked={form.subscribeNewsletter} onChange={handleChange} className="h-4 w-4 text-biguard-orange focus:ring-biguard-orange border-gray-300 rounded" />
                    <label htmlFor="subscribeNewsletter" className="ml-2 block text-sm text-gray-700">
                      Subscribe to our newsletter for financial tips and updates
                    </label>
                  </div>
                </div>
                {error && <div className="text-red-500 text-sm">{error}</div>}
                <button type="submit" className="w-full bg-biguard-orange hover:bg-biguard-orange-dark text-white py-2 px-4 rounded-lg font-medium transition-colors" disabled={loading}>
                  {loading ? 'Creating Account...' : 'Create Account'}
                </button>
              </form>
              <div className="mt-6 text-center">
                <p className="text-sm text-gray-600">
                  Already have an account? <a href="/login" className="text-biguard-orange hover:underline font-medium">Sign in here</a>
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Signup; 