import { Building2, MapPin, ExternalLink, Trash2 } from 'lucide-react'
import { Job } from '../api/client'
import { StatusBadge } from './StatusBadge'
import { useNavigate } from 'react-router-dom'
import { useDeleteJob } from '../hooks/useJobs'

const SOURCE_COLORS: Record<string, string> = {
  linkedin: 'bg-blue-100 text-blue-700',
  indeed: 'bg-indigo-100 text-indigo-700',
  handshake: 'bg-pink-100 text-pink-700',
  ziprecruiter: 'bg-green-100 text-green-700',
  greenhouse: 'bg-emerald-100 text-emerald-700',
  manual: 'bg-parchment-200 text-gray-700',
}

interface Props {
  job: Job
  dragging?: boolean
}

export function ApplicationCard({ job, dragging }: Props) {
  const navigate = useNavigate()
  const deleteJob = useDeleteJob()

  return (
    <div
      className={`card p-3 cursor-pointer hover:border-brand-300 transition-all select-none ${
        dragging ? 'shadow-2xl rotate-1 opacity-90' : ''
      }`}
      onClick={() => navigate(`/jobs/${job.id}`)}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-sm text-gray-800 truncate">{job.title}</p>
          <div className="flex items-center gap-1 text-gray-600 text-xs mt-0.5">
            <Building2 size={11} />
            <span className="truncate">{job.company}</span>
          </div>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); deleteJob.mutate(job.id) }}
          className="text-gray-500 hover:text-red-600 transition-colors p-0.5 flex-shrink-0"
        >
          <Trash2 size={13} />
        </button>
      </div>

      {/* Location + badges */}
      <div className="flex flex-wrap items-center gap-1.5">
        {job.location && (
          <span className="flex items-center gap-0.5 text-gray-600 text-xs">
            <MapPin size={10} />
            {job.location}
          </span>
        )}
        {job.source && (
          <span className={`badge text-[10px] px-1.5 py-0 ${SOURCE_COLORS[job.source] ?? 'bg-parchment-200 text-gray-700'}`}>
            {job.source}
          </span>
        )}
        {job.job_type && (
          <span className="badge text-[10px] px-1.5 py-0 bg-parchment-200 text-gray-700">
            {job.job_type}
          </span>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between mt-2 pt-2 border-t border-parchment-300">
        <StatusBadge status={job.status} size="sm" />
        {job.apply_url && (
          <a
            href={job.apply_url}
            target="_blank"
            rel="noreferrer"
            onClick={e => e.stopPropagation()}
            className="text-gray-500 hover:text-brand-600 transition-colors"
          >
            <ExternalLink size={12} />
          </a>
        )}
      </div>
    </div>
  )
}
