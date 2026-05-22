import { Briefcase, Send, PhoneCall, Trophy, TrendingUp, Loader2 } from 'lucide-react'
import { useJobs } from '../hooks/useJobs'
import { useApplications } from '../hooks/useApplications'
import { useProfile } from '../hooks/useProfile'
import { KanbanBoard } from '../components/KanbanBoard'
import { Link, Navigate } from 'react-router-dom'

function StatCard({ icon: Icon, label, value, color }: {
  icon: React.ElementType
  label: string
  value: number
  color: string
}) {
  return (
    <div className="card p-4 flex items-center gap-4">
      <div className={`p-3 rounded-xl ${color}`}>
        <Icon size={20} className="text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-800">{value}</p>
        <p className="text-xs text-gray-600">{label}</p>
      </div>
    </div>
  )
}

export function Dashboard() {
  const { data: profile, isLoading: profileLoading } = useProfile()
  const { data: jobs = [], isLoading } = useJobs()
  const { data: applications = [] } = useApplications()

  // Redirect to onboarding if profile not set up
  if (profileLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 size={32} className="text-brand-600 animate-spin" />
      </div>
    )
  }

  if (!profile?.full_name) {
    return <Navigate to="/onboarding" replace />
  }

  const stats = {
    total: jobs.length,
    applied: applications.filter(a => a.status !== 'pending' && a.status !== 'withdrawn').length,
    interviews: applications.filter(a => ['interview', 'phone_screen'].includes(a.status)).length,
    offers: applications.filter(a => a.status === 'offer').length,
  }

  const responseRate = stats.applied > 0
    ? Math.round((stats.interviews / stats.applied) * 100)
    : 0

  return (
    <div className="flex flex-col gap-6 h-full">
      {/* Stats bar */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Briefcase}   label="Total Jobs Tracked" value={stats.total}     color="bg-brand-600" />
        <StatCard icon={Send}        label="Applications Sent"  value={stats.applied}   color="bg-brand-500" />
        <StatCard icon={PhoneCall}   label="Interviews"         value={stats.interviews} color="bg-brand-400" />
        <StatCard icon={Trophy}      label="Offers"             value={stats.offers}    color="bg-emerald-600" />
      </div>

      {/* Response rate banner */}
      {stats.applied > 0 && (
        <div className="card p-3 flex items-center gap-3 bg-emerald-50 border-emerald-200">
          <TrendingUp size={18} className="text-emerald-700" />
          <span className="text-sm text-gray-700">
            Response rate: <strong className="text-emerald-700">{responseRate}%</strong>
            <span className="text-gray-600 ml-2">({stats.interviews} interviews from {stats.applied} applications)</span>
          </span>
        </div>
      )}

      {/* Kanban */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800">Application Pipeline</h2>
        <Link to="/search" className="btn-primary text-sm py-1.5 px-3">
          + Add Job
        </Link>
      </div>

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          Loading jobs…
        </div>
      ) : jobs.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center">
          <Briefcase size={48} className="text-parchment-300" />
          <div>
            <p className="text-gray-600 font-medium">No jobs tracked yet</p>
            <p className="text-gray-500 text-sm mt-1">Add your first job to get started</p>
          </div>
          <Link to="/search" className="btn-primary">
            Add Your First Job
          </Link>
        </div>
      ) : (
        <div className="flex-1 overflow-x-auto">
          <KanbanBoard jobs={jobs} />
        </div>
      )}
    </div>
  )
}
