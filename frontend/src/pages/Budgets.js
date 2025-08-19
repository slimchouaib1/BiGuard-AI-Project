
import React, { useEffect, useState } from 'react';

const formatCurrency = (amount) => {
  if (amount === undefined || amount === null) return "$0.00";
  return amount.toLocaleString("en-US", { style: "currency", currency: "USD" });
};

const categoryList = [
  'Food & Drinks', 'Shopping', 'Travel', 'Bills & Utilities', 'Subscriptions',
  'Business Services', 'Insurance & Financial', 'Banking & Fees', 'Fitness & Sports', 'Others'
];

const Budgets = () => {
  const [budgets, setBudgets] = useState([]);
  const [newBudget, setNewBudget] = useState({ category: '', amount: '', period: 'monthly' });
  const [editId, setEditId] = useState(null);
  const [editBudget, setEditBudget] = useState({ category: '', amount: '', period: 'monthly' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Helper to get user_id from localStorage
  const getUserId = () => localStorage.getItem('user_id');

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    fetch('/api/budgets', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => setBudgets(data))
      .catch(() => setBudgets([]));
  }, [success]);

  const handleChange = (e) => {
    setNewBudget({ ...newBudget, [e.target.name]: e.target.value });
  };
  const handleEditChange = (e) => {
    setEditBudget({ ...editBudget, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError(''); setSuccess('');
    const token = localStorage.getItem('access_token');
    fetch('/api/budgets', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        category: newBudget.category,
        amount: parseFloat(newBudget.amount),
        period: newBudget.period
      })
    })
      .then(res => res.json())
      .then(data => {
        if (data.error) setError(data.error);
        else {
          setSuccess('Budget added!');
          setNewBudget({ category: '', amount: '', period: 'monthly' });
        }
      })
      .catch(() => setError('Failed to add budget'));
  };

  const handleEdit = (b) => {
    setEditId(b.id);
    setEditBudget({ category: b.category, amount: b.amount, period: b.period });
  };

  const handleEditSubmit = (e) => {
    e.preventDefault();
    setError(''); setSuccess('');
    const token = localStorage.getItem('access_token');
    fetch(`/api/budgets/${editId}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        category: editBudget.category,
        amount: parseFloat(editBudget.amount),
        period: editBudget.period
      })
    })
      .then(res => res.json())
      .then(data => {
        if (data.error) setError(data.error);
        else {
          setSuccess('Budget updated!');
          setEditId(null);
        }
      })
      .catch(() => setError('Failed to update budget'));
  };

  const handleDelete = (id) => {
    setError(''); setSuccess('');
    const token = localStorage.getItem('access_token');
    fetch(`/api/budgets/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => {
        if (data.error) setError(data.error);
        else setSuccess('Budget deleted!');
      })
      .catch(() => setError('Failed to delete budget'));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-blue-50">
      <header className="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
        <div className="container mx-auto flex h-16 items-center justify-between px-4 md:px-6">
          <div className="flex items-center space-x-2">
            <svg className="h-8 w-8 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            <span className="text-xl font-bold text-gray-900">BiGuard</span>
          </div>
          <nav className="hidden md:flex items-center space-x-8">
            <a href="/dashboard" className="text-[#FF6A00] font-medium">Dashboard</a>
            <a href="/budgets" className="text-[#FF6A00] font-medium">Budgets</a>
            <a href="/savings" className="text-[#FF6A00] font-medium">Savings</a>
          </nav>
        </div>
      </header>
      <section className="w-full py-12 md:py-20 lg:py-28 xl:py-32">
        <div className="container mx-auto px-4 md:px-6">
          <div className="flex flex-col items-center justify-center space-y-4 text-center mb-8">
            <h1 className="text-4xl md:text-5xl font-black tracking-tight text-[#FF6A00] mb-2">Budgets</h1>
            <p className="max-w-2xl text-gray-600 md:text-xl">Set, edit, and track your monthly budgets by category. Stay on top of your spending goals with BiGuard.</p>
          </div>
          <div className="flex flex-col md:flex-row gap-8 justify-center items-start">
            {/* Add Budget Form */}
            <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-lg p-8 flex flex-col gap-4 w-full md:w-1/3">
              <h2 className="text-xl font-bold text-[#FF6A00] mb-2">Add New Budget</h2>
              <div>
                <label className="block text-sm font-medium mb-1">Category</label>
                <select name="category" value={newBudget.category} onChange={handleChange} className="border rounded px-3 py-2 w-full">
                  <option value="">Select category</option>
                  {categoryList.map(cat => <option key={cat} value={cat}>{cat}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Amount</label>
                <input type="number" name="amount" value={newBudget.amount} onChange={handleChange} className="border rounded px-3 py-2 w-full" min="0" step="0.01" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Period</label>
                <select name="period" value={newBudget.period} onChange={handleChange} className="border rounded px-3 py-2 w-full">
                  <option value="monthly">Monthly</option>
                  <option value="weekly">Weekly</option>
                  <option value="yearly">Yearly</option>
                </select>
              </div>
              <button type="submit" className="bg-[#FF6A00] text-white px-6 py-2 rounded font-semibold shadow hover:bg-orange-600 transition-colors">Add Budget</button>
              {error && <div className="text-red-500 text-sm mt-2">{error}</div>}
              {success && <div className="text-green-600 text-sm mt-2">{success}</div>}
            </form>
            {/* Budgets List */}
            <div className="flex-1 w-full">
              <h2 className="text-xl font-bold text-[#FF6A00] mb-4">Your Budgets</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {budgets.length === 0 ? (
                  <div className="col-span-full text-center py-8 text-gray-500 bg-white rounded-xl shadow">No budgets set.</div>
                ) : budgets.map(b => (
                  <div key={b.id} className="bg-white rounded-xl shadow-lg p-6 flex flex-col gap-2 relative group">
                    {editId === b.id ? (
                      <form onSubmit={handleEditSubmit} className="flex flex-col gap-2">
                        <select name="category" value={editBudget.category} onChange={handleEditChange} className="border rounded px-3 py-2">
                          {categoryList.map(cat => <option key={cat} value={cat}>{cat}</option>)}
                        </select>
                        <input type="number" name="amount" value={editBudget.amount} onChange={handleEditChange} className="border rounded px-3 py-2" min="0" step="0.01" />
                        <select name="period" value={editBudget.period} onChange={handleEditChange} className="border rounded px-3 py-2">
                          <option value="monthly">Monthly</option>
                          <option value="weekly">Weekly</option>
                          <option value="yearly">Yearly</option>
                        </select>
                        <div className="flex gap-2 mt-2">
                          <button type="submit" className="bg-[#FF6A00] text-white px-4 py-1 rounded font-semibold hover:bg-orange-600">Save</button>
                          <button type="button" className="bg-gray-200 text-gray-700 px-4 py-1 rounded font-semibold hover:bg-gray-300" onClick={() => setEditId(null)}>Cancel</button>
                        </div>
                      </form>
                    ) : (
                      <>
                        <div className="text-lg font-bold text-[#333333]">{b.category}</div>
                        <div className="text-2xl font-black text-[#FF6A00]">{formatCurrency(b.amount)}</div>
                        <div className="text-sm text-gray-500">{b.period.charAt(0).toUpperCase() + b.period.slice(1)}</div>
                        <div className="absolute top-2 right-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button className="text-blue-600 hover:underline text-xs font-semibold" onClick={() => handleEdit(b)}>Edit</button>
                          <button className="text-red-600 hover:underline text-xs font-semibold" onClick={() => handleDelete(b.id)}>Delete</button>
                        </div>
                      </>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Budgets;
