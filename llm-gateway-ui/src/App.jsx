import React, { useState, useEffect } from 'react';
import { BarChart3, Activity, Coins, ShieldAlert, RefreshCw, Layers, Percent } from 'lucide-react';

export default function App() {
  const [range, setRange] = useState('today');
  const [metrics, setMetrics] = useState({
    summary: {
      total_cached_prompts: 0,
      total_tokens_saved: 0,
      total_usd_saved: 0,
      cache_hit_rate_percentage: 0
    },
    top_users: [],
    daily_trends: { labels: [], hits: [], misses: [] }
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/analytics/dashboard?range=${range}`, {
        method: "GET",
        headers: {
          "X-API-KEY": "gw_P6Jlrt3ErXFUXOJADiseS33vcq7JsJr8FJtUBKyJ0Sc" 
        }
      });
      
      if (!res.ok) {
        throw new Error(`Server error! Status: ${res.status}`);
      }
      const data = await res.json();
      
      if (data.summary) {
        setMetrics(data);
      } else {
        throw new Error("Invalid analytics layout signature received.");
      }
    } catch (err) {
      console.error(err);
      setError("Authorization failed or your AI Gateway is offline!");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
  fetchMetrics();

  const interval = setInterval(() => {
    fetchMetrics();
  }, 15000); 

  return () => clearInterval(interval);
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
          <p className="text-sm text-zinc-400 mt-1">Real-time metrics, semantic caching layers and resource utilization tracking</p>
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
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        
        {/* Panel 1: Tokens Saved */}
        <div className="bg-zinc-900/60 border border-zinc-900 shadow-sm p-6 rounded-xl relative overflow-hidden group hover:border-zinc-800 transition-all duration-300">
          <div className="flex justify-between items-start">
            <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Tokens Saved (Cache)</p>
            <Coins className="h-4 w-4 text-zinc-500 group-hover:text-amber-500 transition-colors" />
          </div>
          <h3 className="text-4xl font-extrabold mt-4 tracking-tight text-zinc-100">
            {loading ? "..." : metrics.summary.total_tokens_saved.toLocaleString()}
          </h3>
          <p className="text-xs text-amber-500 font-medium mt-3">
            ⚡ Context cost bypass metrics
          </p>
        </div>

        {/* Panel 2: Financial Savings */}
        <div className="bg-zinc-900/60 border border-zinc-900 shadow-sm p-6 rounded-xl relative overflow-hidden group hover:border-zinc-800 transition-all duration-300 bg-gradient-to-br from-zinc-900/60 to-emerald-950/10">
          <div className="flex justify-between items-start">
            <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Estimated Cost Saved</p>
            <span className="text-xs font-bold text-emerald-500/80 bg-emerald-500/10 px-2 py-0.5 rounded-full">USD</span>
          </div>
          <h3 className="text-4xl font-extrabold mt-4 tracking-tight text-emerald-500">
            {loading ? "$..." : `$${Number(metrics.summary.total_usd_saved).toFixed(6)}`}
          </h3>
          <p className="text-xs text-zinc-500 mt-3">
            💵 Gemini billing volume saved
          </p>
        </div>

        {/* Panel 3: Cache Hit Rate Percentage */}
        <div className="bg-zinc-900/60 border border-zinc-900 shadow-sm p-6 rounded-xl relative overflow-hidden group hover:border-zinc-800 transition-all duration-300">
        <div className="flex justify-between items-start">
          <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Cache Hit Efficiency</p>
          <Percent className="h-4 w-4 text-zinc-500 group-hover:text-cyan-500 transition-colors" />
        </div>
        <h3 className="text-4xl font-extrabold mt-4 tracking-tight text-cyan-400">
          {loading ? "..." : `${metrics.summary.cache_hit_rate_percentage}%`}
        </h3>
        <p className="text-xs text-cyan-500 font-medium mt-3">
          🎯 Exact + Semantic Match performance
        </p>
      </div>

        {/* Panel 4: Vector Index Size */}
        <div className="bg-zinc-900/60 border border-zinc-900 shadow-sm p-6 rounded-xl relative overflow-hidden group hover:border-zinc-800 transition-all duration-300">
          <div className="flex justify-between items-start">
            <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Cached Vectors Space</p>
            <Layers className="h-4 w-4 text-zinc-500 group-hover:text-purple-500 transition-colors" />
          </div>
          <h3 className="text-4xl font-extrabold mt-4 tracking-tight text-purple-400">
            {loading ? "..." : metrics.summary.total_cached_prompts}
          </h3>
          <p className="text-xs text-purple-500 font-medium mt-3">
            📦 Vectors in MongoDB Collection
          </p>
        </div>

      </div>

    </div>
  );
}