import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Play, Loader2, CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react'
import { getPipelineRuns, runPipeline, PipelineRun } from '../api/pipeline'
import { formatDistanceToNow } from 'date-fns'

export function PipelinePage() {
  const qc = useQueryClient()
  const { data: runs, isLoading } = useQuery({
    queryKey: ['pipeline-runs'],
    queryFn: () => getPipelineRuns(20),
    refetchInterval: 10_000, // poll while viewing
  })

  const trigger = useMutation({
    mutationFn: runPipeline,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline-runs'] }),
  })

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header & Explanation */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Automation Pipeline</h1>
          <p className="text-gray-600 text-sm mt-1">
            Complete workflow: discover jobs → score matches → enrich details → prepare applications → submit
          </p>
        </div>
        <button
          className="btn-primary flex items-center gap-2 px-6 py-3 text-base"
          onClick={() => trigger.mutate()}
          disabled={trigger.isPending}
        >
          {trigger.isPending ? <Loader2 size={18} className="animate-spin" /> : <Play size={18} />}
          {trigger.isPending ? 'Running...' : 'Run Now'}
        </button>
      </div>

      {/* Info Card */}
      <div className="card p-5 bg-blue-50 border-blue-300">
        <p className="text-sm text-blue-900">
          <strong>What happens:</strong> AI discovers jobs matching your preferences, scores them 1-10,
          enriches details with AI analysis, prepares tailored documents, and auto-submits high-scoring applications.
          Monitor progress below.
        </p>
      </div>

      {/* Latest Run Summary */}
      {runs && runs.length > 0 && <LatestRunCard run={runs[0]} />}

      {/* Run History */}
      <div className="card overflow-hidden">
        <div className="px-5 py-3 border-b border-parchment-300">
          <h3 className="font-semibold text-gray-800 text-sm">Run History</h3>
        </div>
        {isLoading ? (
          <div className="flex items-center justify-center py-12 text-gray-400">
            <Loader2 size={20} className="animate-spin" />
          </div>
        ) : !runs || runs.length === 0 ? (
          <div className="text-center py-12 text-gray-500 text-sm">
            No pipeline runs yet. Click "Run Now" to start the first one.
          </div>
        ) : (
          <div className="divide-y divide-parchment-200">
            {runs.map((run) => (
              <RunRow key={run.id} run={run} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function LatestRunCard({ run }: { run: PipelineRun }) {
  const isRunning = run.status === 'running'
  const isFailed = run.status === 'failed'

  return (
    <div
      className={`card p-5 border-l-4 ${
        isRunning
          ? 'border-l-blue-500 bg-blue-50/50'
          : isFailed
          ? 'border-l-red-500 bg-red-50/50'
          : 'border-l-emerald-500 bg-emerald-50/50'
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <StatusIcon status={run.status} />
          <span className="font-semibold text-gray-800 text-sm">Latest Run #{run.id}</span>
          <span className="text-xs text-gray-500">
            ({run.trigger === 'manual' ? 'manual' : 'scheduled'})
          </span>
        </div>
        {run.started_at && (
          <span className="text-xs text-gray-500">
            {formatDistanceToNow(new Date(run.started_at), { addSuffix: true })}
          </span>
        )}
      </div>
      <div className="grid grid-cols-3 md:grid-cols-6 gap-3 text-center">
        <Stat label="Discovered" value={run.jobs_discovered} />
        <Stat label="Scored" value={run.jobs_scored} />
        <Stat label="Enriched" value={run.jobs_enriched} />
        <Stat label="Prepared" value={run.applications_prepared} />
        <Stat label="Submitted" value={run.applications_submitted} />
        <Stat label="Review" value={run.applications_queued_for_review} />
      </div>
      {run.errors && run.errors.length > 0 && (
        <div className="mt-3 space-y-1">
          {run.errors.map((err, i) => (
            <p key={i} className="text-xs text-red-700 flex items-start gap-1">
              <AlertTriangle size={12} className="mt-0.5 flex-shrink-0" />
              <span>
                <strong>{err.stage}:</strong> {err.message}
              </span>
            </p>
          ))}
        </div>
      )}
    </div>
  )
}

function RunRow({ run }: { run: PipelineRun }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="px-5 py-3 hover:bg-parchment-50 cursor-pointer" onClick={() => setExpanded(!expanded)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <StatusIcon status={run.status} />
          <span className="text-sm font-medium text-gray-700">Run #{run.id}</span>
          <span className="text-xs text-gray-400">{run.trigger}</span>
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span>{run.jobs_discovered} discovered</span>
          <span>{run.applications_submitted} submitted</span>
          {run.started_at && (
            <span>{formatDistanceToNow(new Date(run.started_at), { addSuffix: true })}</span>
          )}
        </div>
      </div>
      {expanded && run.errors && run.errors.length > 0 && (
        <div className="mt-2 pl-8 space-y-1">
          {run.errors.map((err, i) => (
            <p key={i} className="text-xs text-red-600">
              [{err.stage}] {err.message}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <CheckCircle size={16} className="text-emerald-600" />
    case 'failed':
      return <XCircle size={16} className="text-red-600" />
    case 'running':
      return <Loader2 size={16} className="text-blue-600 animate-spin" />
    default:
      return <Clock size={16} className="text-gray-400" />
  }
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-lg font-bold text-gray-800">{value}</p>
      <p className="text-[10px] text-gray-500 uppercase tracking-wide">{label}</p>
    </div>
  )
}
