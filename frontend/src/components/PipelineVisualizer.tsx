import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Search,
  CheckCircle,
  AlertCircle,
  Clock,
  Loader2,
  ChevronDown,
  ChevronUp,
  Star,
} from 'lucide-react'
import { getPipelineJobs, PipelineJobOut } from '../api/pipeline'
import { formatDistanceToNow } from 'date-fns'

const PIPELINE_STAGES = [
  { id: 'discovered', label: 'Discovered', color: 'bg-blue-100 border-blue-300', icon: Search },
  { id: 'scored', label: 'Scored', color: 'bg-purple-100 border-purple-300', icon: Star },
  { id: 'enriched', label: 'Enriched', color: 'bg-indigo-100 border-indigo-300', icon: AlertCircle },
  { id: 'prepared', label: 'Prepared', color: 'bg-amber-100 border-amber-300', icon: Clock },
  { id: 'review', label: 'Review', color: 'bg-orange-100 border-orange-300', icon: AlertCircle },
  { id: 'submitted', label: 'Submitted', color: 'bg-green-100 border-green-300', icon: CheckCircle },
]

interface PipelineVisualizerProps {
  refetchInterval?: number
}

export function PipelineVisualizer({ refetchInterval = 5000 }: PipelineVisualizerProps) {
  const [expandedStage, setExpandedStage] = useState<string>('review') // Focus on review stage by default
  const [selectedJob, setSelectedJob] = useState<PipelineJobOut | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['pipeline-jobs'],
    queryFn: () => getPipelineJobs(),
    refetchInterval: refetchInterval,
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-800">Pipeline Visualizer</h2>
        <p className="text-gray-600 text-sm mt-1">
          Track jobs through each stage of the automation pipeline
        </p>
      </div>

      {/* Pipeline Overview Stats */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
          {PIPELINE_STAGES.map((stage) => {
            const count = data.by_stage[stage.id] || 0
            const Icon = stage.icon
            return (
              <div
                key={stage.id}
                className={`${stage.color} border rounded-lg p-3 text-center cursor-pointer hover:shadow-md transition`}
                onClick={() => setExpandedStage(expandedStage === stage.id ? '' : stage.id)}
              >
                <Icon size={16} className="mx-auto mb-1 text-gray-600" />
                <p className="text-lg font-bold text-gray-800">{count}</p>
                <p className="text-[10px] text-gray-600 uppercase tracking-wide">{stage.label}</p>
              </div>
            )
          })}
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="card p-4 bg-red-50 border-red-300">
          <p className="text-sm text-red-700">Failed to load pipeline data</p>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 size={20} className="animate-spin text-blue-600" />
        </div>
      )}

      {/* Pipeline Stages */}
      {data && !isLoading && (
        <div className="space-y-3">
          {PIPELINE_STAGES.map((stage) => {
            const jobs = data.jobs_by_stage[stage.id] || []
            const isExpanded = expandedStage === stage.id
            const Icon = stage.icon

            return (
              <div key={stage.id} className={`card border ${stage.color}`}>
                {/* Stage Header */}
                <div
                  className="px-5 py-3 cursor-pointer hover:bg-gray-50 flex items-center justify-between"
                  onClick={() => setExpandedStage(isExpanded ? '' : stage.id)}
                >
                  <div className="flex items-center gap-3">
                    <Icon size={18} className="text-gray-600" />
                    <div>
                      <h3 className="font-semibold text-gray-800 text-sm">{stage.label}</h3>
                      <p className="text-xs text-gray-500">{jobs.length} jobs</p>
                    </div>
                  </div>
                  {isExpanded ? (
                    <ChevronUp size={18} className="text-gray-400" />
                  ) : (
                    <ChevronDown size={18} className="text-gray-400" />
                  )}
                </div>

                {/* Jobs List */}
                {isExpanded && jobs.length > 0 && (
                  <div className="border-t border-gray-200 divide-y divide-gray-200">
                    {jobs.map((job) => (
                      <JobCard
                        key={job.id}
                        job={job}
                        isSelected={selectedJob?.id === job.id}
                        onSelect={() => setSelectedJob(selectedJob?.id === job.id ? null : job)}
                      />
                    ))}
                  </div>
                )}

                {/* Empty State */}
                {isExpanded && jobs.length === 0 && (
                  <div className="px-5 py-4 text-center text-sm text-gray-500">
                    No jobs in this stage
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Job Detail Panel */}
      {selectedJob && (
        <JobDetailPanel job={selectedJob} onClose={() => setSelectedJob(null)} />
      )}
    </div>
  )
}

interface JobCardProps {
  job: PipelineJobOut
  isSelected: boolean
  onSelect: () => void
}

function JobCard({ job, isSelected, onSelect }: JobCardProps) {
  return (
    <div
      className={`px-5 py-3 hover:bg-gray-50 cursor-pointer transition border-l-4 ${
        isSelected ? 'border-l-blue-500 bg-blue-50' : 'border-l-transparent'
      }`}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-gray-800 text-sm truncate">{job.title}</h4>
          <p className="text-xs text-gray-600">{job.company}</p>
          {job.location && <p className="text-xs text-gray-500">{job.location}</p>}
          {job.score !== null && (
            <div className="flex items-center gap-2 mt-1">
              <span className="inline-block px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                Score: {job.score}/10
              </span>
              {job.source && <span className="text-[10px] text-gray-500">{job.source}</span>}
            </div>
          )}
        </div>
        <div className="text-right">
          {job.created_at && (
            <p className="text-xs text-gray-500">
              {formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

interface JobDetailPanelProps {
  job: PipelineJobOut
  onClose: () => void
}

function JobDetailPanel({ job, onClose }: JobDetailPanelProps) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-start justify-between">
          <div>
            <h3 className="text-lg font-bold text-gray-800">{job.title}</h3>
            <p className="text-gray-600">{job.company}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl font-bold"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Basic Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Location</p>
              <p className="text-sm font-medium text-gray-800">{job.location || 'N/A'}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Source</p>
              <p className="text-sm font-medium text-gray-800">{job.source}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Score</p>
              <p className="text-sm font-medium text-gray-800">
                {job.score !== null ? `${job.score}/10` : 'Not scored'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Pipeline Stage</p>
              <p className="text-sm font-medium text-gray-800 capitalize">{job.pipeline_stage}</p>
            </div>
          </div>

          {/* Score Analysis */}
          {job.score !== null && (
            <div className="space-y-2">
              <h4 className="font-semibold text-gray-800 text-sm">Score Analysis</h4>
              {job.score_reasoning && (
                <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded">
                  {job.score_reasoning}
                </p>
              )}
              {job.score_strengths && job.score_strengths.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-600 mb-1">Strengths:</p>
                  <ul className="text-sm text-gray-700 space-y-1">
                    {job.score_strengths.map((strength, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-green-600 mt-0.5">✓</span>
                        <span>{strength}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {job.score_concerns && job.score_concerns.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-600 mb-1">Concerns:</p>
                  <ul className="text-sm text-gray-700 space-y-1">
                    {job.score_concerns.map((concern, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-orange-600 mt-0.5">!</span>
                        <span>{concern}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Enrichment Data */}
          {job.enrichment_data && (
            <div>
              <h4 className="font-semibold text-gray-800 text-sm mb-2">Enrichment Notes</h4>
              <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded">{job.enrichment_data}</p>
            </div>
          )}

          {/* Action Links */}
          {job.apply_url && (
            <div>
              <a
                href={job.apply_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-700 text-sm font-medium"
              >
                → View Job Posting
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
