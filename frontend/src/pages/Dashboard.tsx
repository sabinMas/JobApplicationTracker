import React from 'react';
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { dashboardAPI } from '../api/dashboard';

const Dashboard: React.FC = () => {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: () => dashboardAPI.getMetrics(7),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-white">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-red-400">Failed to load dashboard data</p>
      </div>
    );
  }

  const sourceData = Object.entries(metrics.by_source || {}).map(([name, value]) => ({
    name,
    value,
  }));

  const atsPlatformData = Object.entries(metrics.by_ats_platform || {}).map(([name, value]) => ({
    name,
    value,
  }));

  const scoreDistributionData = [
    { name: 'High (8-10)', value: metrics.score_distribution?.high || 0 },
    { name: 'Medium (5-7)', value: metrics.score_distribution?.medium || 0 },
    { name: 'Low (1-4)', value: metrics.score_distribution?.low || 0 },
  ];

  const COLORS = ['#22c55e', '#f59e0b', '#ef4444'];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold text-white mb-2">Dashboard</h1>
        <p className="text-gray-400 mb-8">Real-time job application tracking and metrics</p>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-slate-700/50 backdrop-blur p-6 rounded-lg border border-slate-600">
            <p className="text-gray-400 text-sm mb-1">Jobs Discovered</p>
            <h3 className="text-3xl font-bold text-white">{metrics.total_jobs_discovered}</h3>
          </div>
          <div className="bg-slate-700/50 backdrop-blur p-6 rounded-lg border border-slate-600">
            <p className="text-gray-400 text-sm mb-1">Applications</p>
            <h3 className="text-3xl font-bold text-white">{metrics.total_applications}</h3>
          </div>
          <div className="bg-slate-700/50 backdrop-blur p-6 rounded-lg border border-slate-600">
            <p className="text-gray-400 text-sm mb-1">Success Rate</p>
            <h3 className="text-3xl font-bold text-white">{(metrics.success_rate * 100).toFixed(1)}%</h3>
          </div>
          <div className="bg-slate-700/50 backdrop-blur p-6 rounded-lg border border-slate-600">
            <p className="text-gray-400 text-sm mb-1">Avg Score</p>
            <h3 className="text-3xl font-bold text-white">{metrics.average_score.toFixed(1)}</h3>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <div className="bg-slate-700/50 backdrop-blur p-6 rounded-lg border border-slate-600">
            <h2 className="text-xl font-semibold text-white mb-6">Score Distribution</h2>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={scoreDistributionData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}`}
                  outerRadius={100}
                  dataKey="value"
                >
                  {COLORS.map((color, index) => (
                    <Cell key={`cell-${index}`} fill={color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none' }} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-slate-700/50 backdrop-blur p-6 rounded-lg border border-slate-600">
            <h2 className="text-xl font-semibold text-white mb-6">Jobs by Source</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={sourceData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#4b5563" />
                <XAxis dataKey="name" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none' }} />
                <Bar dataKey="value" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-slate-700/50 backdrop-blur p-6 rounded-lg border border-slate-600">
          <h2 className="text-xl font-semibold text-white mb-6">Applications by ATS Platform</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={atsPlatformData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#4b5563" />
              <XAxis dataKey="name" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none' }} />
              <Bar dataKey="value" fill="#8b5cf6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export { Dashboard };