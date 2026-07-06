import React, { useState, useEffect } from 'react';
import { BarChart3, Activity, Coins, ShieldAlert, RefreshCw } from 'lucide-react';

export default function App() {
  const [range, setRange] = useState('today');
  const [metrics, setMetrics] = useState({ total_requests: 0, total_tokens: 0, total_cost: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/analytics/dashboard?range=${range}`);
      if (!res.ok) {
        throw new Error(`Server gave ${res.status} status `);
      }
      const data = await res.json();
      setMetrics(data);
    } catch (err) {
      console.error("Fetch block error:", err);
      setError("Backend unreachable or CORS issue");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, [range]);

  return (
    <div className="p-8 bg-zinc-950 min-h-screen text-zinc-100 font-sans antialiased">
      
      {/* 🟢 Top Control Console */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-10 border-b border-zinc-800 pb-6 gap-4">
        <div>
          <div className="flex items-center gap-2">
            <BarChart3 className="text-amber-500 h-6 w-6" />
            <h1 className="text-2xl font-bold tracking-tight text-zinc-100">LLM Gateway Engine</h1>
          </div>
          <p className="text-sm text-zinc-400 mt-1">Real-time metrics, tokens overhead and billing diagnostics</p>
        </div>
        
        {/* Actions Layout */}
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button 
            onClick={fetchMetrics}
            className="p-2.5 bg-zinc-900 border border-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
            title="Refresh Data"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          
          <select 
            value={range} 
            onChange={(e) => setRange(e.target.value)}
            className="w-full sm:w-40 bg-zinc-900 border border-zinc-800 text-sm rounded-lg p-2.5 focus:ring-1 focus:ring-amber-500 focus:border-amber-500 text-zinc-200 cursor-pointer focus:outline-none"
          >
            <option value="today">Today</option>
            <option value="7days">Last 7 Days</option>
            <option value="30days">Last 30 Days</option>
            <option value="all">All Time</option>
          </select>
        </div>
      </div>

      {/* ⚠️ Error Alert Flag */}
      {error && (
        <div className="mb-6 p-4 bg-red-950/40 border border-red-900/50 rounded-xl flex items-center gap-3 text-red-400 text-sm">
          <ShieldAlert className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 📊 Metrics Panels Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Panel 1: Requests Count */}
        <div className="bg-zinc-900/60 border border-zinc-950/40 shadow-sm p-6 rounded-xl relative overflow-hidden group hover:border-zinc-800 transition-all duration-300">
          <div className="flex justify-between items-start">
            <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Total Traffic Volume</p>
            <Activity className="h-4 w-4 text-zinc-500 group-hover:text-emerald-500 transition-colors" />
          </div>
          <h3 className="text-4xl font-extrabold mt-4 tracking-tight text-zinc-100">
            {loading ? "..." : metrics.total_requests}
          </h3>
          <p className="text-xs text-emerald-500 font-medium mt-3 flex items-center gap-1">
            <span>● Gateway proxies active</span>
          </p>
        </div>

        {/* Panel 2: Compute Tokens Overhead */}
        <div className="bg-zinc-900/60 border border-zinc-950/40 shadow-sm p-6 rounded-xl relative overflow-hidden group hover:border-zinc-800 transition-all duration-300">
          <div className="flex justify-between items-start">
            <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Compute Tokens Consumed</p>
            <Coins className="h-4 w-4 text-zinc-500 group-hover:text-amber-500 transition-colors" />
          </div>
          <h3 className="text-4xl font-extrabold mt-4 tracking-tight text-zinc-100">
            {loading ? "..." : metrics.total_tokens.toLocaleString()}
          </h3>
          <p className="text-xs text-amber-500 font-medium mt-3">
            ~ Compiled context processing metrics
          </p>
        </div>

        {/* Panel 3: Financial Overhead */}
        <div className="bg-zinc-900/60 border border-zinc-950/40 shadow-sm p-6 rounded-xl relative overflow-hidden group hover:border-zinc-800 transition-all duration-300 bg-gradient-to-br from-zinc-900/60 to-amber-950/10">
          <div className="flex justify-between items-start">
            <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Estimated Cost Aggregation</p>
            <span className="text-xs font-bold text-amber-500/80 bg-amber-500/10 px-2 py-0.5 rounded-full">USD</span>
          </div>
          <h3 className="text-4xl font-extrabold mt-4 tracking-tight text-amber-500">
            {loading ? "$..." : `$${Number(metrics.total_cost).toFixed(6)}`}
          </h3>
          <p className="text-xs text-zinc-500 mt-3">
            Precision algorithmic resource pricing
          </p>
        </div>

      </div>

    </div>
  );
}