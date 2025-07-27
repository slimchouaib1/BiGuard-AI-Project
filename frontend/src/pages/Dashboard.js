import React, { useState, useEffect, useCallback, useRef } from 'react';
import { PlaidLink } from 'react-plaid-link';

// Helper for currency formatting
const formatCurrency = (amount) => {
  if (amount === undefined || amount === null) return "$0.00";
  return amount.toLocaleString("en-US", { style: "currency", currency: "USD" });
};

const Dashboard = () => {
  const [tab, setTab] = useState('overview');
  const [dashboardData, setDashboardData] = useState(null);
  const [error, setError] = useState('');
  const [linkToken, setLinkToken] = useState(null);
  const [linkError, setLinkError] = useState('');
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState('');
  // Add missing state for accounts and transactions
  const [accounts, setAccounts] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [showAll, setShowAll] = useState(false);
  const [search, setSearch] = useState("");

  // Refs for section navigation
  const checkingRef = useRef(null);
  const savingsRef = useRef(null);

  // Plaid Link success handler (memoized)
  const handlePlaidSuccess = useCallback(async (publicToken) => {
    const token = localStorage.getItem('access_token');
    try {
      const response = await fetch('/api/plaid/exchange-token', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ public_token: publicToken })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Plaid token exchange failed');
      // Optionally, re-sync transactions after linking
      syncTransactions();
    } catch (err) {
      setLinkError(err.message);
    }
  }, []);

  // useCallback for PlaidLink
  const onPlaidSuccess = useCallback(async (public_token) => {
    await handlePlaidSuccess(public_token);
  }, [handlePlaidSuccess]);


  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    // Helper to check if any account is a Plaid sandbox account
    const isSandbox = (accountsList) => {
      // Plaid sandbox access tokens start with 'access-sandbox-'
      return accountsList && accountsList.some(acc => acc.plaid_access_token && acc.plaid_access_token.startsWith('access-sandbox-'));
    };

    // Step 1: Fetch accounts first to check for sandbox
    fetch('/api/accounts', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(async data => {
        setAccounts(data.accounts || []);
        // If using Plaid sandbox, trigger backend to generate a lot of transactions
        if (isSandbox(data.accounts)) {
          await fetch('/api/plaid/sandbox/generate-transactions', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
          });
        }
        // Now fetch dashboard data and sync all transactions
        fetch('/api/dashboard/stats', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
          .then(res => res.json())
          .then(data => setDashboardData(data))
          .catch(() => setError('Failed to load dashboard data'));
        // Fetch Plaid link token
        fetch('/api/plaid/create-link-token', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        })
          .then(res => res.json())
          .then(data => setLinkToken(data.link_token))
          .catch(() => setLinkError('Could not create Plaid link token'));
        // Always sync all transactions (per_page=200)
        syncTransactions();
      })
      .catch(() => setAccounts([]));
  }, []);

  // Automatically open Plaid Link when linkToken is set and user has not linked a bank
  useEffect(() => {
    if (linkToken) {
      setTimeout(() => {
        const openPlaid = document.getElementById('auto-plaid-link');
        if (openPlaid) openPlaid.click();
      }, 500);
    }
  }, [linkToken]);

  const syncTransactions = async () => {
    setSyncing(true);
    setSyncError('');
    const token = localStorage.getItem('access_token');
    try {
      // Fetch all transactions (not just recent)
      const response = await fetch('/api/transactions?per_page=200', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Sync failed');
      setTransactions(data.transactions || []);
    } catch (err) {
      setSyncError(err.message);
    } finally {
      setSyncing(false);
    }
  };



  // User and account data
  const user = dashboardData?.user || { firstName: 'User', lastName: 'Name' };
  const checking = dashboardData?.checking;
  const savings = dashboardData?.savings;

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-blue-50">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur">
        <div className="container mx-auto flex h-16 items-center justify-between px-4 md:px-6">
          <a href="/" className="flex items-center space-x-2">
            <svg className="h-8 w-8 text-[#FF6A00]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            <span className="text-2xl font-bold text-[#333333]">BiGuard</span>
          </a>
          <nav className="hidden md:flex items-center space-x-8">
            <a href="#checking" className="text-[#FF6A00] font-medium" onClick={e => { e.preventDefault(); checkingRef.current?.scrollIntoView({ behavior: 'smooth' }); }}>Checking</a>
            <a href="#savings" className="text-[#FF6A00] font-medium" onClick={e => { e.preventDefault(); savingsRef.current?.scrollIntoView({ behavior: 'smooth' }); }}>Savings</a>
          </nav>
          <div className="flex items-center space-x-4">
            <div className="w-8 h-8 bg-[#FF6A00] rounded-full flex items-center justify-center text-white font-medium">
              {user.firstName.charAt(0)}{user.lastName.charAt(0)}
            </div>
            <span className="hidden md:block text-sm font-medium text-[#333333]">{user.firstName}</span>
            <button className="p-2 text-gray-600 hover:text-[#FF6A00]">Logout</button>
          </div>
        </div>
      </header>
      {/* Profile Section */}
      <div className="container mx-auto px-4 pt-8 pb-2 flex flex-col md:flex-row items-center md:items-end justify-between">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-[#FF6A00] to-[#FFB347] flex items-center justify-center text-white text-3xl font-bold shadow-lg">
            {user.firstName.charAt(0)}{user.lastName.charAt(0)}
          </div>
          <div>
            <div className="text-lg md:text-2xl font-bold text-[#333333]">Welcome back, {user.firstName}!</div>
            <div className="text-sm text-gray-500">Your AI-powered financial dashboard</div>
          </div>
        </div>
        {/* Removed Profile and Logout buttons as requested */}
      </div>
      {/* Main Content: Full-width vertical sections */}
      <main className="container mx-auto px-4 py-6 space-y-16">
        {/* Checking Section */}
        <section ref={checkingRef} id="checking" className="w-full mb-16">
          {checking && (
            <div className="bg-white rounded-2xl shadow-xl p-8 flex flex-col items-center">
              <h2 className="text-4xl font-black mb-4 tracking-tight uppercase" style={{ color: '#FF6A00', fontFamily: 'Montserrat, Inter, Arial, sans-serif', letterSpacing: 1, textShadow: '0 2px 8px rgba(255,106,0,0.08)' }}>Checking Accounts</h2>
              <div className="flex flex-col md:flex-row gap-8 w-full justify-center mb-6">
                <div className="bg-biguard-orange/10 rounded-xl p-6 flex-1 text-center">
                  <div className="text-lg font-semibold text-biguard-orange">Total Balance</div>
                  <div className="text-3xl font-bold text-biguard-orange">{formatCurrency(checking.current_balance)}</div>
                </div>
                <div className="bg-green-100 rounded-xl p-6 flex-1 text-center">
                  <div className="text-lg font-semibold text-green-700">Monthly Net Income</div>
                  <div className="text-3xl font-bold text-green-700">{formatCurrency(checking.monthly_net_income)}</div>
                </div>
              </div>
              <div className="mb-4 w-full">
                <div className="font-semibold text-gray-700 mb-1">Accounts</div>
                <ul className="flex flex-wrap gap-2 mb-2">
                  {checking.accounts?.map(acc => (
                    <li key={acc.id} className="bg-gray-100 px-3 py-1 rounded text-sm font-semibold">
                      {acc.name} <span className="text-gray-400">({acc.current_balance && formatCurrency(acc.current_balance)})</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="mb-6 w-full">
                <div className="font-semibold mb-2 text-gray-700">Category Breakdown & Budgets</div>
                {checking.category_breakdown && Object.keys(checking.category_breakdown).length > 0 ? (
                  <ul className="text-base">
                    {Object.entries(checking.category_breakdown).map(([cat, amt]) => {
                      const budget = checking.budgets?.[cat];
                      const overBudget = budget && amt > budget.amount;
                      return (
                        <li key={cat} className={overBudget ? 'text-red-600 font-semibold' : ''}>
                          <span className="inline-block w-40 font-medium">{cat}</span>: {formatCurrency(amt)}
                          {budget && (
                            <span className="ml-2 text-xs text-gray-500">(Budget: {formatCurrency(budget.amount)} / {budget.period})</span>
                          )}
                          {overBudget && <span className="ml-2 text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">Over Budget</span>}
                        </li>
                      );
                    })}
                  </ul>
                ) : <div className="text-gray-400">No data</div>}
              </div>
              <div className="mb-6 w-full">
                <div className="font-semibold mb-2 text-gray-700">Fraud Alerts <span className="ml-2 text-red-500 font-bold">{checking.fraud_alerts_count || 0}</span></div>
                {checking.fraud_alerts?.length > 0 && (
                  <ul className="mt-2 text-base">
                    {checking.fraud_alerts.map(alert => (
                      <li key={alert.id} className="mb-1">{alert.date}: {alert.name} <span className="text-red-600">({formatCurrency(alert.amount)})</span> Score: {alert.fraud_score}</li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="w-full">
                <div className="font-semibold mb-2 text-gray-700 flex items-center justify-between">
                  <span>Recent Transactions</span>
                  <input
                    type="text"
                    placeholder="Search by name or date..."
                    className="border border-gray-300 rounded px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-[#FF6A00]"
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    style={{ minWidth: 220 }}
                  />
                </div>
                <div className="overflow-x-auto max-h-96" style={{ maxHeight: '24rem', overflowY: 'auto' }}>
                  <table className="min-w-full bg-white rounded-lg shadow">
                    <thead>
                      <tr>
                        <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Date</th>
                        <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Name</th>
                        <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Amount</th>
                        <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Category</th>
                        <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(() => {
                        // Filter transactions for display
                        let txs = checking.transactions || [];
                        if (search) {
                          const s = search.toLowerCase();
                          txs = txs.filter(tx =>
                            (tx.name && tx.name.toLowerCase().includes(s)) ||
                            (tx.date && tx.date.includes(s))
                          );
                        }
                        if (txs.length === 0) {
                          return (
                            <tr>
                              <td colSpan="5" className="text-center py-4 text-gray-500">No transactions found.</td>
                            </tr>
                          );
                        }
                        return txs.map(tx => (
                          <tr key={tx.id}>
                            <td className="px-4 py-2 text-sm text-gray-700">{tx.date}</td>
                            <td className="px-4 py-2 text-sm text-gray-700">{tx.name}</td>
                            <td className="px-4 py-2 text-sm text-[#FF6A00] font-bold">{formatCurrency(tx.amount)}</td>
                            <td className="px-4 py-2 text-sm text-gray-700">{tx.category}</td>
                            <td className="px-4 py-2 text-sm">{tx.pending ? <span className="text-yellow-500">Pending</span> : <span className="text-green-600">Posted</span>}</td>
                          </tr>
                        ));
                      })()}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </section>
        {/* Savings Section */}
        <section ref={savingsRef} id="savings" className="w-full mb-16">
          {savings && (
            <div className="bg-white rounded-2xl shadow-xl p-8 flex flex-col items-center">
              <h2 className="text-4xl font-black mb-4 tracking-tight uppercase" style={{ color: '#FF6A00', fontFamily: 'Montserrat, Inter, Arial, sans-serif', letterSpacing: 1, textShadow: '0 2px 8px rgba(255,106,0,0.08)' }}>Savings Accounts</h2>
              <div className="flex flex-col md:flex-row gap-8 w-full justify-center mb-6">
                <div className="bg-[#FFEDD5] rounded-xl p-6 flex-1 text-center">
                  <div className="text-lg font-semibold" style={{ color: '#FF6A00' }}>Total Balance</div>
                  <div className="text-3xl font-bold" style={{ color: '#FF6A00' }}>{formatCurrency(savings.current_balance)}</div>
                </div>
              </div>
              <div className="mb-4 w-full">
                <div className="font-semibold text-gray-700 mb-1">Accounts</div>
                <ul className="flex flex-wrap gap-2 mb-2">
                  {savings.accounts?.map(acc => (
                    <li key={acc.id} className="bg-gray-100 px-3 py-1 rounded text-sm font-semibold">
                      {acc.name} <span className="text-gray-400">({acc.current_balance && formatCurrency(acc.current_balance)})</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="mb-6 w-full">
                <div className="font-semibold mb-2 text-gray-700">Category Breakdown</div>
                {savings.category_breakdown && Object.keys(savings.category_breakdown).length > 0 ? (
                  <ul className="text-base">
                    {Object.entries(savings.category_breakdown).map(([cat, amt]) => (
                      <li key={cat}><span className="inline-block w-40 font-medium">{cat}</span>: {formatCurrency(amt)}</li>
                    ))}
                  </ul>
                ) : <div className="text-gray-400">No data</div>}
              </div>
              <div className="mb-6 w-full">
                <div className="font-semibold mb-2 text-gray-700">Fraud Alerts <span className="ml-2 text-red-500 font-bold">{savings.fraud_alerts_count || 0}</span></div>
                {savings.fraud_alerts?.length > 0 && (
                  <ul className="mt-2 text-base">
                    {savings.fraud_alerts.map(alert => (
                      <li key={alert.id} className="mb-1">{alert.date}: {alert.name} <span className="text-red-600">({formatCurrency(alert.amount)})</span> Score: {alert.fraud_score}</li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="w-full">
                <div className="font-semibold mb-2 text-gray-700">Recent Transactions</div>
                <div className="overflow-x-auto">
                  <table className="min-w-full bg-white rounded-lg shadow">
                    <thead>
                      <tr>
                        <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Date</th>
                        <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Name</th>
                        <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Amount</th>
                        <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Category</th>
                        <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {savings.transactions?.length === 0 ? (
                        <tr>
                          <td colSpan="5" className="text-center py-4 text-gray-500">No transactions found.</td>
                        </tr>
                      ) : (
                        savings.transactions.map(tx => (
                          <tr key={tx.id}>
                            <td className="px-4 py-2 text-sm text-gray-700">{tx.date}</td>
                            <td className="px-4 py-2 text-sm text-gray-700">{tx.name}</td>
                            <td className="px-4 py-2 text-sm text-blue-700 font-bold">{formatCurrency(tx.amount)}</td>
                            <td className="px-4 py-2 text-sm text-gray-700">{tx.category}</td>
                            <td className="px-4 py-2 text-sm">{tx.pending ? <span className="text-yellow-500">Pending</span> : <span className="text-green-600">Posted</span>}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </section>
        {/* Plaid Link Button: Only show if user has NO linked accounts (i.e., first-time user) */}
        {linkToken && accounts.length === 0 && (
          <div className="flex justify-center my-8">
            <PlaidLink
              id="plaid-link-btn"
              token={linkToken}
              onSuccess={onPlaidSuccess}
              className="bg-biguard-orange text-white px-6 py-3 rounded-lg font-semibold shadow hover:bg-orange-600 transition-colors text-lg flex items-center gap-2"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
              Link Bank Account
            </PlaidLink>
          </div>
        )}
        {linkError && <div className="text-red-500 mt-2 text-center">{linkError}</div>}
        {error && <div className="text-red-500 text-center">{error}</div>}
      </main>
    </div>
  );
};

export default Dashboard;