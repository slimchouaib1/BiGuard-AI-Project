import React, { useEffect, useState } from 'react';
import { PlaidLink } from 'react-plaid-link';
import { Bar, Pie } from 'react-chartjs-2';
import 'chart.js/auto';

const formatCurrency = (amount) => {
  if (amount === undefined || amount === null) return "$0.00";
  return amount.toLocaleString("en-US", { style: "currency", currency: "USD" });
};

const Checking = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [linkToken, setLinkToken] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState('');
  const [budgets, setBudgets] = useState({});
  const [advisorTips, setAdvisorTips] = useState([]);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    fetch('/api/dashboard/stats', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => setDashboardData(data))
      .catch(() => {});
    fetch('/api/plaid/create-link-token', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => setLinkToken(data.link_token))
      .catch(() => {});
    fetch('/api/accounts', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => setAccounts(data.accounts || []))
      .catch(() => setAccounts([]));
    fetchBudgets();
    syncTransactions();
  }, []);

  const fetchBudgets = async () => {
    const token = localStorage.getItem('access_token');
    const res = await fetch('/api/budgets', { headers: { 'Authorization': `Bearer ${token}` } });
    const data = await res.json();
    if (data && data.budgets) {
      const byCat = {};
      data.budgets.forEach(b => { byCat[b.category] = b; });
      setBudgets(byCat);
    }
  };

  const syncTransactions = async () => {
    setSyncing(true);
    setSyncError('');
    const token = localStorage.getItem('access_token');
    try {
      const response = await fetch('/api/transactions/sync', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      await response.json();
    } catch (err) {
      setSyncError('Sync failed');
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    if (dashboardData && dashboardData.checking) {
      // Simple advisor logic
      const tips = [];
      if (dashboardData.checking.monthly_net_income < 0) tips.push('Your net income is negative this month. Consider reducing expenses.');
      if (dashboardData.checking.category_breakdown) {
        Object.entries(dashboardData.checking.category_breakdown).forEach(([cat, amt]) => {
          const budget = dashboardData.checking.budgets?.[cat];
          if (budget && amt > budget.amount) tips.push(`You are over budget in ${cat}.`);
        });
      }
      setAdvisorTips(tips);
    }
  }, [dashboardData]);

  if (!dashboardData || !dashboardData.checking) return <div className="p-8">Loading...</div>;
  const checking = dashboardData.checking;

  // Chart data
  const pieData = {
    labels: Object.keys(checking.category_breakdown || {}),
    datasets: [{
      data: Object.values(checking.category_breakdown || {}),
      backgroundColor: [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#E7E9ED'
      ]
    }]
  };
  const barData = {
    labels: Object.keys(checking.category_breakdown || {}),
    datasets: [{
      label: 'Spending by Category',
      data: Object.values(checking.category_breakdown || {}),
      backgroundColor: '#FF6384'
    }]
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto bg-white rounded-2xl shadow-xl p-8">
        <h2 className="text-3xl font-extrabold text-biguard-orange mb-4 tracking-tight">Checking Accounts</h2>
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
          <div className="font-semibold mb-2 text-gray-700">Budgets (Editable)</div>
          <ul className="text-base">
            {Object.entries(budgets).map(([cat, b]) => (
              <li key={cat} className="mb-2 flex items-center gap-2">
                <span className="inline-block w-40 font-medium">{cat}</span>
                <input type="number" className="border rounded px-2 py-1 w-24" defaultValue={b.amount} />
                <span className="text-xs text-gray-500">/ {b.period}</span>
                <button className="bg-biguard-orange text-white px-2 py-1 rounded text-xs">Save</button>
              </li>
            ))}
          </ul>
        </div>
        <div className="mb-6 w-full">
          <div className="font-semibold mb-2 text-gray-700">Spending by Category</div>
          <div className="flex flex-col md:flex-row gap-8">
            <div className="flex-1"><Pie data={pieData} /></div>
            <div className="flex-1"><Bar data={barData} /></div>
          </div>
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
        <div className="mb-6 w-full">
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
                {checking.transactions?.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="text-center py-4 text-gray-500">No transactions found.</td>
                  </tr>
                ) : (
                  checking.transactions.map(tx => (
                    <tr key={tx.id}>
                      <td className="px-4 py-2 text-sm text-gray-700">{tx.date}</td>
                      <td className="px-4 py-2 text-sm text-gray-700">{tx.name}</td>
                      <td className="px-4 py-2 text-sm text-biguard-orange font-bold">{formatCurrency(tx.amount)}</td>
                      <td className="px-4 py-2 text-sm text-gray-700">{tx.category}</td>
                      <td className="px-4 py-2 text-sm">{tx.pending ? <span className="text-yellow-500">Pending</span> : <span className="text-green-600">Posted</span>}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
        <div className="mb-6 w-full">
          <div className="font-semibold mb-2 text-gray-700">Financial Advisor</div>
          <ul className="list-disc pl-6">
            {advisorTips.length === 0 && <li>All good! No major issues detected.</li>}
            {advisorTips.map((tip, i) => <li key={i}>{tip}</li>)}
          </ul>
        </div>
      </div>
    </div>
  );
};

export default Checking;
