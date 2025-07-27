import React, { useEffect, useState } from 'react';

const formatCurrency = (amount) => {
  if (amount === undefined || amount === null) return "$0.00";
  return amount.toLocaleString("en-US", { style: "currency", currency: "USD" });
};

const Savings = () => {
  const [dashboardData, setDashboardData] = useState(null);
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    fetch('/api/dashboard/stats', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => setDashboardData(data))
      .catch(() => {});
  }, []);
  if (!dashboardData || !dashboardData.savings) return <div className="p-8">Loading...</div>;
  const savings = dashboardData.savings;
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto bg-white rounded-2xl shadow-xl p-8">
        <h2 className="text-3xl font-extrabold text-blue-700 mb-4 tracking-tight">Savings Accounts</h2>
        <div className="flex flex-col md:flex-row gap-8 w-full justify-center mb-6">
          <div className="bg-blue-100 rounded-xl p-6 flex-1 text-center">
            <div className="text-lg font-semibold text-blue-700">Total Balance</div>
            <div className="text-3xl font-bold text-blue-700">{formatCurrency(savings.current_balance)}</div>
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
    </div>
  );
};

export default Savings;
