import React, { useState, useEffect, useCallback, useRef } from 'react';
import { PlaidLink } from 'react-plaid-link';
import ChatWidget from './ChatWidget';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar, Pie } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

// Helper for currency formatting
const formatCurrency = (amount) => {
  if (amount === undefined || amount === null) return "$0.00";
  return amount.toLocaleString("en-US", { style: "currency", currency: "USD" });
};

// Chart data processing functions
const prepareCategoryChartData = (categoryBreakdown) => {
  if (!categoryBreakdown || Object.keys(categoryBreakdown).length === 0) {
    return null;
  }

  const categories = Object.keys(categoryBreakdown);
  const amounts = Object.values(categoryBreakdown).map(amount => Math.abs(amount));

  // Generate colors for each category
  const colors = [
    '#FF6A00', '#FFB347', '#FF8C42', '#FFA726', '#FF9800',
    '#FF5722', '#FF7043', '#FF8A65', '#FFAB91', '#FFCC02',
    '#4CAF50', '#8BC34A', '#CDDC39', '#FFEB3B', '#FFC107'
  ];

  return {
    labels: categories,
    datasets: [{
      data: amounts,
      backgroundColor: colors.slice(0, categories.length),
      borderColor: colors.slice(0, categories.length).map(color => color + '80'),
      borderWidth: 2,
      hoverOffset: 4,
    }]
  };
};

const prepareIncomeExpenseChartData = (monthlyIncome, monthlyExpenses) => {
  return {
    labels: ['Income', 'Expenses'],
    datasets: [{
      label: 'Amount ($)',
      data: [Math.abs(monthlyIncome || 0), Math.abs(monthlyExpenses || 0)],
      backgroundColor: ['#4CAF50', '#FF5722'],
      borderColor: ['#45a049', '#e64a19'],
      borderWidth: 1,
      borderRadius: 8,
    }]
  };
};

const prepareTransactionTrendsData = (transactions) => {
  if (!transactions || transactions.length === 0) {
    return null;
  }

  // Group transactions by date and calculate daily totals
  const dailyTotals = {};
  transactions.forEach(tx => {
    const date = tx.date;
    if (!dailyTotals[date]) {
      dailyTotals[date] = { income: 0, expenses: 0 };
    }
    
    if (tx.is_expense !== false) {
      dailyTotals[date].expenses += Math.abs(tx.amount);
    } else {
      dailyTotals[date].income += Math.abs(tx.amount);
    }
  });

  // Sort dates and take last 30 days
  const sortedDates = Object.keys(dailyTotals).sort().slice(-30);
  
  return {
    labels: sortedDates,
    datasets: [
      {
        label: 'Income',
        data: sortedDates.map(date => dailyTotals[date].income),
        borderColor: '#4CAF50',
        backgroundColor: '#4CAF5080',
        fill: true,
        tension: 0.4,
      },
      {
        label: 'Expenses',
        data: sortedDates.map(date => dailyTotals[date].expenses),
        borderColor: '#FF5722',
        backgroundColor: '#FF572280',
        fill: true,
        tension: 0.4,
      }
    ]
  };
};

const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [error, setError] = useState('');
  const [linkToken, setLinkToken] = useState(null);
  const [linkError, setLinkError] = useState('');
  const [linkSuccess, setLinkSuccess] = useState('');
  const [accounts, setAccounts] = useState([]);
  const [showAll, setShowAll] = useState(false);
  const [search, setSearch] = useState("");
  const [showManualEntry, setShowManualEntry] = useState(false);
  const [categories, setCategories] = useState([]);
  const [dataStatus, setDataStatus] = useState(null);
  const [connectingBank, setConnectingBank] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [showAllMonths, setShowAllMonths] = useState(true); // Toggle between current month and 4 months
  const plaidRef = useRef(null);
  const [anomalySummary, setAnomalySummary] = useState(null);
  const [anomalyLoading, setAnomalyLoading] = useState(false);

  const getUserId = useCallback(() => {
    return localStorage.getItem('user_id');
  }, []);

  const fetchDataStatus = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/user/data-status', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        const status = await response.json();
        setDataStatus(status);
      }
    } catch (error) {
      console.error('Error fetching data status:', error);
    }
  }, []);

  const fetchAnomalySummary = useCallback(async () => {
    try {
      setAnomalyLoading(true);
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/anomaly/summary', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        const summary = await response.json();
        setAnomalySummary(summary);
      }
    } catch (error) {
      console.error('Error fetching anomaly summary:', error);
    } finally {
      setAnomalyLoading(false);
    }
  }, []);

  const connectRealBank = useCallback(async () => {
    setConnectingBank(true);
    try {
      const token = localStorage.getItem('access_token');
      
      // Clear sample data first
      const clearResponse = await fetch('/api/connect-real-bank', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (clearResponse.ok) {
        // Create Plaid link token
        const linkResponse = await fetch('/api/plaid/create-link-token', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (linkResponse.ok) {
          const linkData = await linkResponse.json();
          setLinkToken(linkData.link_token);
          // Trigger Plaid Link to open
          setTimeout(() => {
            if (plaidRef.current) {
              plaidRef.current.open();
            }
          }, 100);
        } else {
          setLinkError('Failed to create link token');
        }
      } else {
        setLinkError('Failed to clear sample data');
      }
    } catch (error) {
      console.error('Error connecting real bank:', error);
      setLinkError('Connection failed');
    } finally {
      setConnectingBank(false);
    }
  }, []);

  const syncTransactions = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/plaid/sync-now', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        fetchDashboardData();
      }
    } catch (error) {
      console.error('Error syncing transactions:', error);
    }
  }, []);

  const fetchDashboardData = async () => {
    try {
    const token = localStorage.getItem('access_token');
      const response = await fetch('/api/dashboard/stats', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setDashboardData(data);
        setError('');
      } else {
        setError('Failed to fetch dashboard data');
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setError('Failed to fetch dashboard data');
    }
  };

  const handlePlaidSuccess = async (public_token, metadata) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/plaid/exchange-token', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ public_token })
      });

      if (response.ok) {
        setLinkToken(null);
        setLinkError('');
        setLinkSuccess('Bank account connected successfully!');
        fetchDashboardData();
        fetchDataStatus();
        // Clear success message after 5 seconds
        setTimeout(() => setLinkSuccess(''), 5000);
      } else {
        setLinkError('Failed to connect bank account');
      }
    } catch (error) {
      console.error('Error exchanging token:', error);
      setLinkError('Failed to connect bank account');
    }
  };

  const handlePlaidExit = () => {
    setLinkToken(null);
    setLinkError('');
    setLinkSuccess('');
  };

  useEffect(() => {
    fetchDashboardData();
    fetchDataStatus();
    fetchAnomalySummary();
  }, [fetchDataStatus, fetchAnomalySummary]);

  const generateSampleData = async () => {
    try {
    const token = localStorage.getItem('access_token');
      const response = await fetch('/api/sample-data/generate', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        fetchDashboardData();
        fetchDataStatus();
      }
    } catch (error) {
      console.error('Error generating sample data:', error);
    }
  };

  const clearSampleData = async () => {
    try {
    const token = localStorage.getItem('access_token');
      const response = await fetch('/api/sample-data/clear', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        fetchDashboardData();
        fetchDataStatus();
      }
    } catch (error) {
      console.error('Error clearing sample data:', error);
    }
  };

  const handleClearFraudulentTransactions = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/anomaly/clear-fraudulent', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        fetchAnomalySummary(); // Refresh summary to show updated count
        alert('All fraudulent transactions have been cleared.');
      } else {
        alert('Failed to clear fraudulent transactions.');
      }
    } catch (error) {
      console.error('Error clearing fraudulent transactions:', error);
      alert('Failed to clear fraudulent transactions.');
    }
  };

  // Removed manual training - model is now auto-trained

  if (!dashboardData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading your financial dashboard...</p>
        </div>
      </div>
    );
  }

  const { user, checking, savings } = dashboardData;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex items-center space-x-2">
                  <svg className="h-8 w-8 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
                  <span className="text-xl font-bold text-gray-900">BiGuard</span>
                </div>
              </div>
            </div>

            <nav className="flex space-x-8">
              <a href="/dashboard" className="text-orange-600 border-b-2 border-orange-600 px-3 py-2 text-sm font-medium">Dashboard</a>
              <a href="/savings" className="text-gray-500 hover:text-gray-700 px-3 py-2 text-sm font-medium">Savings</a>
              <a href="/budgets" className="text-gray-500 hover:text-gray-700 px-3 py-2 text-sm font-medium">Budgets</a>
          </nav>

          <div className="flex items-center space-x-4">
              <div className="flex items-center">
                <div className="w-8 h-8 bg-orange-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-sm font-medium">
                    {user?.firstName?.charAt(0)}{user?.lastName?.charAt(0)}
                  </span>
                </div>
                <span className="ml-2 text-sm text-gray-700">{user?.firstName} {user?.lastName}</span>
              </div>
              <button
                onClick={connectRealBank}
                disabled={connectingBank}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {connectingBank ? 'Connecting...' : 'Switch to Real Bank'}
              </button>
              {linkError && (
                <div className="text-red-500 text-xs mt-1">{linkError}</div>
              )}
              {linkSuccess && (
                <div className="text-green-500 text-xs mt-1">{linkSuccess}</div>
              )}
              <button
                onClick={() => {
                  localStorage.removeItem('access_token');
                  localStorage.removeItem('user_id');
                  window.location.href = '/';
                }}
                className="text-gray-500 hover:text-gray-700 text-sm"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Demo Mode Banner */}
      {dataStatus?.has_sample_data && (
        <div className="bg-orange-50 border-l-4 border-orange-400 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-orange-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
          </div>
            <div className="ml-3">
              <p className="text-sm text-orange-700">
                <strong>Demo Mode Active</strong> - You're viewing realistic sample data. Connect your real bank account to see your actual finances.
              </p>
          </div>
        </div>
      </div>
      )}

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <div className="flex items-center">
            <div className="w-16 h-16 bg-orange-500 rounded-full flex items-center justify-center">
              <span className="text-white text-xl font-bold">
                {user?.firstName?.charAt(0)}{user?.lastName?.charAt(0)}
              </span>
             </div>
            <div className="ml-4">
              <h1 className="text-3xl font-bold text-gray-900">Welcome back, {user?.firstName}!</h1>
              <p className="text-gray-600">Your AI-powered financial dashboard</p>
           </div>
         </div>
       </div>

        {/* Sample Data Controls */}
        <div className="mb-6 flex space-x-4">
                     <button
            onClick={generateSampleData}
            className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700"
                     >
                       Generate Sample Data
                     </button>
          <button
            onClick={clearSampleData}
            className="bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-700"
          >
            Clear Sample Data
          </button>
        </div>

        {/* Financial Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-2 bg-green-100 rounded-lg">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Monthly Income</p>
                <p className="text-2xl font-bold text-gray-900">{formatCurrency(checking?.monthly_income || 0)}</p>
              </div>
                   </div>
                 </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-2 bg-red-100 rounded-lg">
                <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Monthly Expenses</p>
                <p className="text-2xl font-bold text-gray-900">{formatCurrency(checking?.monthly_expenses || 0)}</p>
              </div>
                  </div>
                </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 rounded-lg">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Net Income</p>
                <p className="text-2xl font-bold text-gray-900">{formatCurrency(checking?.monthly_net_income || 0)}</p>
                </div>
              </div>
            </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-2 bg-purple-100 rounded-lg">
                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Balance</p>
                <p className="text-2xl font-bold text-gray-900">{formatCurrency(checking?.current_balance || 0)}</p>
                </div>
                </div>
              </div>
            </div>

        {/* Anomaly Detection Card */}
        {anomalySummary && (
          <div className="mb-6">
            <div className={`bg-white rounded-lg shadow p-6 border-l-4 ${
              anomalySummary.risk_level === 'high' ? 'border-red-500' :
              anomalySummary.risk_level === 'medium' ? 'border-yellow-500' :
              'border-green-500'
            }`}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center">
                  <div className={`p-2 rounded-lg ${
                    anomalySummary.risk_level === 'high' ? 'bg-red-100' :
                    anomalySummary.risk_level === 'medium' ? 'bg-yellow-100' :
                    'bg-green-100'
                  }`}>
                    <svg className={`w-6 h-6 ${
                      anomalySummary.risk_level === 'high' ? 'text-red-600' :
                      anomalySummary.risk_level === 'medium' ? 'text-yellow-600' :
                      'text-green-600'
                    }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Real-Time Fraud Detection</p>
                    <p className={`text-2xl font-bold ${
                      anomalySummary.risk_level === 'high' ? 'text-red-600' :
                      anomalySummary.risk_level === 'medium' ? 'text-yellow-600' :
                      'text-green-600'
                    }`}>
                      {anomalySummary.risk_level === 'high' ? '🚨 High Risk' :
                       anomalySummary.risk_level === 'medium' ? '⚠️ Medium Risk' :
                       '✅ Low Risk'}
                    </p>
                    <p className="text-sm text-gray-500">
                      {anomalySummary.total_anomalies} fraudulent transactions detected & blocked
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      AI-powered real-time monitoring active
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <div className="text-sm text-gray-500">
                      <div>High: {anomalySummary.high_severity}</div>
                      <div>Medium: {anomalySummary.medium_severity}</div>
                      <div>Low: {anomalySummary.low_severity}</div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {anomalySummary.total_anomalies > 0 && (
                      <button
                        onClick={handleClearFraudulentTransactions}
                        className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 transition-colors text-sm"
                      >
                        Clear All
                      </button>
                    )}
                  </div>
                </div>
              </div>
              
              {/* Fraudulent Transactions List */}
              {anomalySummary.fraudulent_transactions && anomalySummary.fraudulent_transactions.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-3">Blocked Transactions</h4>
                  <div className="max-h-64 overflow-y-auto border border-gray-200 rounded-md">
                    <div className="divide-y divide-gray-200">
                      {anomalySummary.fraudulent_transactions.map((fraudTx) => (
                        <div key={fraudTx.id} className="p-3 hover:bg-gray-50">
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-center space-x-2">
                                <span className="font-medium text-gray-900">{fraudTx.name}</span>
                                <span className={`px-2 py-1 text-xs rounded-full ${
                                  fraudTx.severity === 'high' ? 'bg-red-100 text-red-800' :
                                  fraudTx.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                                  'bg-blue-100 text-blue-800'
                                }`}>
                                  {fraudTx.severity.toUpperCase()}
                                </span>
                              </div>
                              <div className="text-sm text-gray-600 mt-1">
                                <span className="font-medium">${Math.abs(fraudTx.amount).toFixed(2)}</span>
                                <span className="mx-2">•</span>
                                <span>{fraudTx.category}</span>
                                <span className="mx-2">•</span>
                                <span>{new Date(fraudTx.date).toLocaleDateString()}</span>
                              </div>
                              <div className="text-xs text-gray-500 mt-1">
                                <span className="font-medium">Threat Level:</span> 
                                <span className={`ml-1 px-2 py-1 rounded text-xs ${
                                  fraudTx.threat_level === 'high' ? 'bg-red-100 text-red-800' :
                                  fraudTx.threat_level === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                                  'bg-blue-100 text-blue-800'
                                }`}>
                                  {fraudTx.threat_level?.toUpperCase() || 'MEDIUM'}
                                </span>
                              </div>
                              <div className="text-xs text-gray-500 mt-1">
                                <span className="font-medium">Blocked for:</span> {fraudTx.anomaly_reasons?.join(', ') || fraudTx.reasons?.join(', ') || 'Suspicious activity'}
                              </div>
                              <div className="text-xs text-gray-400 mt-1">
                                Detected: {new Date(fraudTx.detected_at || fraudTx.date).toLocaleString()}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Transactions Section - Moved Above Charts */}
        <div className="mb-8">
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex justify-between items-center">
                <div className="flex items-center space-x-4">
                  <h3 className="text-lg font-semibold text-gray-900">
                    All Transactions {showAllMonths ? '(Last 4 Months)' : '(This Month Only)'}
                  </h3>
                  <button
                    onClick={() => setShowAllMonths(!showAllMonths)}
                    className="px-3 py-1 text-sm bg-orange-500 text-white rounded-md hover:bg-orange-600 transition-colors"
                  >
                    {showAllMonths ? 'Show This Month Only' : 'Show Last 4 Months'}
                  </button>
              </div>
                <div className="flex space-x-2">
                  <input
                    type="text"
                    placeholder="Search transactions..."
                    className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                  <select
                    className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    onChange={(e) => setCategoryFilter(e.target.value)}
                  >
                    <option value="">All Categories</option>
                    {checking?.transactions?.reduce((categories, tx) => {
                      if (!categories.includes(tx.category)) {
                        categories.push(tx.category);
                      }
                      return categories;
                    }, []).map(category => (
                      <option key={category} value={category}>{category}</option>
                    ))}
                  </select>
                </div>
              </div>
                </div>
            <div className="overflow-x-auto">
              <div className="max-h-96 overflow-y-auto"> {/* Scrollable container */}
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Transaction</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
                      </tr>
                    </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {checking?.transactions
                      ?.filter(transaction => {
                        // Filter by date range based on toggle
                        const transactionDate = new Date(transaction.date);
                        const now = new Date();
                        const currentMonth = new Date(now.getFullYear(), now.getMonth(), 1);
                        
                        if (!showAllMonths && transactionDate < currentMonth) {
                          return false;
                        }
                        
                        const matchesSearch = !searchTerm || 
                          transaction.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          (transaction.merchant_name && transaction.merchant_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
                          transaction.category.toLowerCase().includes(searchTerm.toLowerCase());
                        const matchesCategory = !categoryFilter || transaction.category === categoryFilter;
                        return matchesSearch && matchesCategory;
                      })
                      .map((transaction) => (
                        <tr key={transaction.id} className={transaction.is_fraudulent ? 'bg-red-50 border-l-4 border-red-500' : ''}>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm font-medium text-gray-900">
                              {transaction.name}
                              {transaction.is_fraudulent && (
                                <span className="ml-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                  🚨 BLOCKED
                                </span>
                              )}
                            </div>
                            <div className="text-sm text-gray-500">{transaction.merchant_name || ''}</div>
                            {transaction.is_fraudulent && transaction.anomaly_reasons && (
                              <div className="text-xs text-red-600 mt-1">
                                {transaction.anomaly_reasons.join(', ')}
                              </div>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                              {transaction.category}
                            </span>
                            {transaction.is_fraudulent && (
                              <div className="mt-1">
                                <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                  transaction.threat_level === 'high' ? 'bg-red-100 text-red-800' :
                                  transaction.threat_level === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                                  'bg-blue-100 text-blue-800'
                                }`}>
                                  {transaction.threat_level?.toUpperCase() || 'MEDIUM'} THREAT
                                </span>
                              </div>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {new Date(transaction.date).toLocaleDateString()}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <span className={transaction.is_expense ? 'text-red-600' : 'text-green-600'}>
                              {transaction.is_expense ? '-' : '+'}{formatCurrency(Math.abs(transaction.amount))}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

        {/* Charts Section */}
        {checking && (
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Financial Insights & Analytics</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Income vs Expenses Chart */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Monthly Income vs Expenses</h3>
                <Bar
                  data={prepareIncomeExpenseChartData(checking.monthly_income, checking.monthly_expenses)}
                  options={{
                    responsive: true,
                    plugins: {
                      legend: {
                        position: 'top',
                      },
                      tooltip: {
                        callbacks: {
                          label: function(context) {
                            return `${context.label}: ${formatCurrency(context.parsed.y)}`;
                          }
                        }
                      }
                    },
                    scales: {
                      y: {
                        beginAtZero: true,
                        ticks: {
                          callback: function(value) {
                            return formatCurrency(value);
                          }
                        }
                      }
                    }
                  }}
                 />
               </div>

              {/* Category Breakdown Chart */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Spending by Category</h3>
                {prepareCategoryChartData(checking.category_breakdown) ? (
                  <Pie
                    data={prepareCategoryChartData(checking.category_breakdown)}
                    options={{
                      responsive: true,
                      plugins: {
                        legend: {
                          position: 'bottom',
                        },
                        tooltip: {
                          callbacks: {
                            label: function(context) {
                              const total = context.dataset.data.reduce((a, b) => a + b, 0);
                              const percentage = ((context.parsed / total) * 100).toFixed(1);
                              return `${context.label}: ${formatCurrency(context.parsed)} (${percentage}%)`;
                            }
                          }
                        }
                      }
                    }}
                  />
                ) : (
                  <div className="flex items-center justify-center h-64 text-gray-500">
                    No category data available
               </div>
                )}
               </div>

              {/* Transaction Trends Chart */}
              <div className="bg-white rounded-lg shadow p-6 lg:col-span-2">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Transaction Trends (Last 4 Months)</h3>
                {prepareTransactionTrendsData(checking.transactions) ? (
                  <Line
                    data={prepareTransactionTrendsData(checking.transactions)}
                    options={{
                      responsive: true,
                      plugins: {
                        legend: {
                          position: 'top',
                        },
                        tooltip: {
                          callbacks: {
                            label: function(context) {
                              return `${context.dataset.label}: ${formatCurrency(context.parsed.y)}`;
                            }
                          }
                        }
                      },
                      scales: {
                        y: {
                          beginAtZero: true,
                          ticks: {
                            callback: function(value) {
                              return formatCurrency(value);
                            }
                          }
                        }
                      }
                    }}
                  />
                ) : (
                  <div className="flex items-center justify-center h-64 text-gray-500">
                    No transaction data available
               </div>
                )}
             </div>
           </div>
         </div>
       )}
            </div>

      {/* Plaid Link */}
      {linkToken && (
        <PlaidLink
          ref={plaidRef}
          token={linkToken}
          onSuccess={handlePlaidSuccess}
          onExit={handlePlaidExit}
          className="hidden"
          style={{ display: 'none' }}
        />
      )}

      {/* Chat Widget */}
      <ChatWidget />
     </div>
   );
 };

const DashboardWithChat = () => {
  return <Dashboard />;
};

export default DashboardWithChat;
