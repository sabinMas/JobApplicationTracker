import React from 'react';
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { dashboardAPI } from '../api/dashboard';
import { getProfile, getJobs, getApplications } from '../api/client';
import { AlertCircle, Zap, ExternalLink, Briefcase, CheckCircle } from 'lucide-react';

const Dashboard: React.FC = () => {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: () => dashboardAPI.getMetrics(7),
  });

  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn: getProfile,
  });

  const { data: jobs = [] } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => getJobs({ status: 'discovered' }),
  });

  const { data: applications = [] } = useQuery({
    queryKey: ['applications'],
    queryFn: getApplications,
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

  // Check setup completion
  const hasProfile = profile && (profile.skills?.length || profile.experience?.length || profile.full_name);
  const totalJobs = metrics.total_jobs_discovered || 0;

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

        {/* Onboarding Guidance */}
        {!hasProfile && (
          <div className="mb-8 bg-amber-900/30 border border-amber-600/50 rounded-lg p-6 flex gap-4">
            <AlertCircle className="text-amber-400 flex-shrink-0" size={24} />
            <div className="flex-1">
              <h3 className="text-white font-semibold mb-2">Get Started: Upload Your Resume</h3>
              <p className="text-gray-300 text-sm mb-4">
                To begin, go to <strong>Profile</strong> and upload your resume PDF. We'll extract your information
                and use it to find perfectly matched job opportunities.
              </p>
              <a href="/profile" className="inline-block bg-amber-600 hover:bg-amber-700 text-white px-4 py-2 rounded font-medium text-sm transition-colors">
                Go to Profile
              </a>
            </div>
          </div>
        )}

        {hasProfile && totalJobs === 0 && (
          <div className="mb-8 bg-blue-900/30 border border-blue-600/50 rounded-lg p-6 flex gap-4">
            <Zap className="text-blue-400 flex-shrink-0" size={24} />
            <div className="flex-1">
              <h3 className="text-white font-semibold mb-2">Ready to Find Jobs?</h3>
              <p className="text-gray-300 text-sm mb-4">
                Your profile is set up! Go to <strong>Preferences</strong> to define what jobs you're looking for,
                then click <strong>Run Now</strong> on the <strong>Pipeline</strong> page to discover matching opportunities.
              </p>
              <div className="flex gap-3">
                <a href="/preferences" className="inline-block bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium text-sm transition-colors">
                  Set Preferences
                </a>
                <a href="/pipeline" className="inline-block bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded font-medium text-sm transition-colors">
                  Go to Pipeline
                </a>
              </div>
            </div>
          </div>
        )}

        {/* Recent Jobs & Applications Tracker */}
        {(jobs.length > 0 || applications.length > 0) && (
          <div className="mb-8">
            <h2 className="text-xl font-semibold text-white mb-4">Activity Tracker</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* High-Scoring Jobs Ready for Review */}
              {jobs.filter(j => (j.score || 0) >= 8).length > 0 && (
                <div className="bg-slate-700/50 backdrop-blur p-6 rounded-lg border border-emerald-600/30">
                  <h3 className="text-lg font-semibold text-emerald-400 mb-4 flex items-center gap-2">
                    <Briefcase size={20} />
                    High-Scoring Jobs ({jobs.filter(j => (j.score || 0) >= 8).length})
                  </h3>
                  <div className="space-y-3 max-h-64 overflow-y-auto">
                    {jobs
                      .filter(j => (j.score || 0) >= 8)
                      .sort((a, b) => (b.score || 0) - (a.score || 0))
                      .slice(0, 5)
                      .map(job => (
                        <div key={job.id} className="bg-slate-600/30 p-3 rounded text-sm">
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <p className="font-medium text-white">{job.title}</p>
                              <p className="text-gray-400 text-xs">{job.company} • {job.location}</p>
                            </div>
                            <span className="bg-emerald-600/40 text-emerald-300 px-2 py-1 rounded text-xs font-semibold ml-2">
                              {job.score}/10
                            </span>
                          </div>
                          {job.apply_url && (
                            <a
                              href={job.apply_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-400 hover:text-blue-300 text-xs mt-2 inline-flex items-center gap-1"
                            >
                              View Job <ExternalLink size={12} />
                            </a>
                          )}
                        </div>
                      ))}
                  </div>
                </div>
              )}

              {/* Recent Applications */}
              {applications.length > 0 && (
                <div className="bg-slate-700/50 backdrop-blur p-6 rounded-lg border border-blue-600/30">
                  <h3 className="text-lg font-semibold text-blue-400 mb-4 flex items-center gap-2">
                    <CheckCircle size={20} />
                    Recent Applications ({applications.length})
                  </h3>
                  <div className="space-y-3 max-h-64 overflow-y-auto">
                    {applications
                      .sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime())
                      .slice(0, 5)
                      .map(app => {
                        const job = jobs.find(j => j.id === app.job_id);
                        return (
                          <div key={app.id} className="bg-slate-600/30 p-3 rounded text-sm">
                            <div className="flex justify-between items-start">
                              <div className="flex-1">
                                <p className="font-medium text-white">{job?.title || 'Unknown Job'}</p>
                                <p className="text-gray-400 text-xs">{job?.company || 'Unknown'}</p>
                              </div>
                              <span
                                className={`px-2 py-1 rounded text-xs font-semibold ml-2 ${
                                  app.status === 'applied'
                                    ? 'bg-green-600/40 text-green-300'
                                    : app.status === 'pending'
                                    ? 'bg-yellow-600/40 text-yellow-300'
                                    : 'bg-gray-600/40 text-gray-300'
                                }`}
                              >
                                {app.status === 'applied' ? '✓ Applied' : app.status === 'pending' ? 'Pending' : app.status}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

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
            <h3 className="text-3xl font-bold text-white">{((metrics.success_rate ?? 0) * 100).toFixed(1)}%</h3>
          </div>
          <div className="bg-slate-700/50 backdrop-blur p-6 rounded-lg border border-slate-600">
            <p className="text-gray-400 text-sm mb-1">Avg Score</p>
            <h3 className="text-3xl font-bold text-white">{(metrics.scoring_stats?.avg_score ?? 0).toFixed(1)}</h3>
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