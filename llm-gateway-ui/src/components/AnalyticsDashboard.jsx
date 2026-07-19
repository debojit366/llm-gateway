import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, BarChart, Bar } from 'recharts';
import { Calendar, Cpu, DollarSign, Activity, Zap } from 'lucide-react';

const AnalyticsDashboard = () => {
  const [range, setRange] = useState('today');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAnalytics = async (selectedRange) => {
    setLoading(true);
    try {
      const manualApiKey = import.meta.env.VITE_LLM_GATEWAY_API_KEY
      
      const response = await fetch(`http://localhost:8000/api/v1/analytics/dashboard?range=${selectedRange}`, {
        method: "GET",
        headers: {
          "X-API-Key": manualApiKey, 
          "Content-Type": "application/json"
        }
      });
      
      if (!response.ok) throw new Error(`Dashboard metrics pull failed! Status: ${response.status}`);
      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics(range);
    
    const interval = setInterval(() => fetchAnalytics(range), 10000);
    return () => clearInterval(interval);
  }, [range]);

  if (loading && !data) return <div className="text-white p-6">Loading dynamic matrices bhai...</div>;
  if (error) return <div className="text-red-400 p-6">Error: {error}</div>;

  const chartData = data?.daily_trends?.labels.map((label, index) => ({
    name: label,
    Hits: data.daily_trends.hits[index] || 0,
    Misses: data.daily_trends.misses[index] || 0,
  })) || [];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 font-sans">
      {/* HEADER SECTION */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
            AI Gateway Analytics
          </h1>
          <p className="text-slate-400 text-sm mt-1">Real-time LLM caching footprint and consumer distribution</p>
        </div>

        {/* TIME RANGE TABS */}
        <div className="flex bg-slate-900 p-1 rounded-xl border border-slate-800">
          {['today', '7days', '30days', 'all'].map((tab) => (
            <button
              key={tab}
              onClick={() => setRange(tab)}
              className={`px-4 py-2 text-xs font-semibold uppercase rounded-lg transition-all ${
                range === tab 
                  ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg shadow-cyan-500/20' 
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab === '7days' ? '7 Days' : tab === '30days' ? '30 Days' : tab}
            </button>
          ))}
        </div>
      </div>

      {/* 📊 SUMMARY BADGES / CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        
        {/* TOTAL CACHED PROMPTS */}
        <div className="bg-slate-900 border border-slate-800/80 p-5 rounded-2xl relative overflow-hidden group">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-slate-400">Cached Prompts</p>
              <h3 className="text-2xl font-bold mt-2 text-white">{data?.summary?.total_cached_prompts}</h3>
            </div>
            <div className="p-3 bg-cyan-500/10 text-cyan-400 rounded-xl"><Zap size={20} /></div>
          </div>
          <div className="absolute bottom-0 left-0 h-[2px] w-0 bg-cyan-500 group-hover:w-full transition-all duration-300" />
        </div>

        {/* TOTAL TOKENS SAVED */}
        <div className="bg-slate-900 border border-slate-800/80 p-5 rounded-2xl relative overflow-hidden group">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-slate-400">Tokens Saved</p>
              <h3 className="text-2xl font-bold mt-2 text-emerald-400">
                {data?.summary?.total_tokens_saved.toLocaleString()}
              </h3>
            </div>
            <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-xl"><Cpu size={20} /></div>
          </div>
          <div className="absolute bottom-0 left-0 h-[2px] w-0 bg-emerald-500 group-hover:w-full transition-all duration-300" />
        </div>

        {/* LIVE REVENUE / COST SAVED BADGE */}
        <div className="bg-slate-900 border border-slate-800/80 p-5 rounded-2xl relative overflow-hidden group">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-slate-400">Revenue Saved (USD)</p>
              <h3 className="text-2xl font-bold mt-2 text-amber-400">
                ${data?.summary?.total_usd_saved ? data.summary.total_usd_saved.toFixed(5) : "0.00000"}
              </h3>
            </div>
            <div className="p-3 bg-amber-500/10 text-amber-400 rounded-xl"><DollarSign size={20} /></div>
          </div>
          <div className="absolute bottom-0 left-0 h-[2px] w-0 bg-amber-500 group-hover:w-full transition-all duration-300" />
        </div>

        {/* CACHE HIT EFFICIENCY */}
        <div className="bg-slate-900 border border-slate-800/80 p-5 rounded-2xl relative overflow-hidden group">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-slate-400">Cache Hit Rate</p>
              <h3 className="text-2xl font-bold mt-2 text-indigo-400">
                {data?.summary?.cache_hit_rate_percentage}%
              </h3>
            </div>
            <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl"><Activity size={20} /></div>
          </div>
          <div className="absolute bottom-0 left-0 h-[2px] w-0 bg-indigo-500 group-hover:w-full transition-all duration-300" />
        </div>

      </div>

      {/* CHARTS GRID METRICS SECTION */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* 📈 REAL-TIME DAILY TRENDS (AREA CHART) */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 p-6 rounded-2xl">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Calendar size={18} className="text-cyan-400" /> Daily Cache Analysis (Hits vs Misses)
          </h2>
          <div className="h-[320px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorHits" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorMisses" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '12px' }}
                  labelStyle={{ color: '#94a3b8', fontWeight: 'bold' }}
                />
                <Legend verticalAlign="top" height={36} iconType="circle" />
                <Area type="monotone" dataKey="Hits" stroke="#06b6d4" strokeWidth={2} fillOpacity={1} fill="url(#colorHits)" />
                <Area type="monotone" dataKey="Misses" stroke="#6366f1" strokeWidth={2} fillOpacity={1} fill="url(#colorMisses)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 👑 USER / MODEL TOKENS USED DISTRIBUTION CHART */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl flex flex-col justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
              <Cpu size={18} className="text-amber-400" /> Model / User Distribution
            </h2>
            <p className="text-xs text-slate-400 mb-4">Top utilization matrix sorted by traffic volume</p>
            
            <div className="h-[200px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data?.top_users || []} margin={{ top: 5, right: 5, left: -25, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis dataKey="user_id" stroke="#64748b" fontSize={10} tickLine={false} />
                  <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '8px' }}
                    itemStyle={{ color: '#f59e0b' }}
                  />
                  <Bar dataKey="requests" fill="#f59e0b" radius={[4, 4, 0, 0]} maxBarSize={30} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* LIST VIEWS FOR EXACT NUMBERS */}
          <div className="mt-4 space-y-3">
            {data?.top_users?.map((item, idx) => (
              <div key={idx} className="flex justify-between items-center p-2 rounded-lg bg-slate-950 border border-slate-800/60 text-xs">
                <span className="font-mono text-slate-300 truncate max-w-[160px]">{item.user_id}</span>
                <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 font-bold">
                  {item.requests} reqs
                </span>
              </div>
            ))}
          </div>

        </div>

      </div>
    </div>
  );
};

export default AnalyticsDashboard;