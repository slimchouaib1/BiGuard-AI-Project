import React, { useState, useEffect } from 'react';

const Dashboard = () => {
  const [tab, setTab] = useState('overview');
  const [dashboardData, setDashboardData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    // Fetch dashboard data from backend with JWT token
    const token = localStorage.getItem('access_token');
    fetch('/api/dashboard/stats', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
      .then(res => {
        if (!res.ok) throw new Error('Unauthorized');
        return res.json();
      })
      .then(data => setDashboardData(data))
      .catch(() => setError('Failed to load dashboard data'));
  }, []);

  // Placeholder user data
  const user = dashboardData?.user || { firstName: 'User', lastName: 'Name', monthlyIncome: 0, monthlyExpenses: 0, accountBalance: 0 };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur">
        <div className="container mx-auto flex h-16 items-center justify-between px-4 md:px-6">
          <a href="/" className="flex items-center space-x-2">
            <svg className="h-8 w-8 text-biguard-orange" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            <span className="text-2xl font-bold text-biguard-gray">BiGuard</span>
          </a>
          <nav className="hidden md:flex items-center space-x-8">
            <a href="/dashboard" className="text-biguard-orange font-medium">Dashboard</a>
            <a href="/transactions" className="text-biguard-gray hover:text-biguard-orange transition-colors">Transactions</a>
            <a href="/budgets" className="text-biguard-gray hover:text-biguard-orange transition-colors">Budgets</a>
            <a href="/reports" className="text-biguard-gray hover:text-biguard-orange transition-colors">Reports</a>
          </nav>
          <div className="flex items-center space-x-4">
            <div className="w-8 h-8 bg-biguard-orange rounded-full flex items-center justify-center text-white font-medium">
              {user.firstName.charAt(0)}{user.lastName.charAt(0)}
            </div>
            <span className="hidden md:block text-sm font-medium text-biguard-gray">{user.firstName}</span>
            <button className="p-2 text-gray-600 hover:text-biguard-orange">Logout</button>
          </div>
        </div>
      </header>
      {/* Main Content */}
      <main className="container mx-auto px-4 py-6 space-y-6">
        {/* Welcome Section & Quick Stats */}
        <div className="grid gap-6 md:grid-cols-4">
          <div className="md:col-span-2 bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h1 className="text-2xl font-bold text-biguard-gray">Welcome back, {user.firstName}!</h1>
                <p className="text-gray-600">Here's your financial overview for today</p>
              </div>
              <div className="w-12 h-12 bg-biguard-orange rounded-full flex items-center justify-center text-white font-medium">
                {user.firstName.charAt(0)}{user.lastName.charAt(0)}
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-3xl font-bold text-biguard-gray">${user.accountBalance}</span>
            </div>
            <p className="text-sm text-gray-600 mt-1">Total Balance</p>
          </div>
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-700">Monthly Income</h3>
              <svg className="h-4 w-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <div className="text-2xl font-bold text-green-600">${user.monthlyIncome}</div>
            <p className="text-xs text-gray-600">+12% from last month</p>
          </div>
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-700">Monthly Expenses</h3>
              <svg className="h-4 w-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
              </svg>
            </div>
            <div className="text-2xl font-bold text-red-600">${user.monthlyExpenses}</div>
            <p className="text-xs text-gray-600">+5% from last month</p>
          </div>
        </div>
        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-lg">
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8 px-6" aria-label="Tabs">
              <button className={`tab-button py-4 px-1 border-b-2 font-medium text-sm ${tab === 'overview' ? 'border-biguard-orange text-biguard-orange' : 'border-transparent text-gray-500'}`} onClick={() => setTab('overview')}>Overview</button>
              <button className={`tab-button py-4 px-1 border-b-2 font-medium text-sm ${tab === 'transactions' ? 'border-biguard-orange text-biguard-orange' : 'border-transparent text-gray-500'}`} onClick={() => setTab('transactions')}>Transactions</button>
              <button className={`tab-button py-4 px-1 border-b-2 font-medium text-sm ${tab === 'budgets' ? 'border-biguard-orange text-biguard-orange' : 'border-transparent text-gray-500'}`} onClick={() => setTab('budgets')}>Budgets</button>
              <button className={`tab-button py-4 px-1 border-b-2 font-medium text-sm ${tab === 'analytics' ? 'border-biguard-orange text-biguard-orange' : 'border-transparent text-gray-500'}`} onClick={() => setTab('analytics')}>Analytics</button>
            </nav>
          </div>
          <div className="p-6">
            {tab === 'overview' && <div>Overview Content</div>}
            {tab === 'transactions' && <div>Transactions Content</div>}
            {tab === 'budgets' && <div>Budgets Content</div>}
            {tab === 'analytics' && <div>Analytics Content</div>}
          </div>
        </div>
        {error && <div className="text-red-500 text-center">{error}</div>}
      </main>
    </div>
  );
};

export default Dashboard; 