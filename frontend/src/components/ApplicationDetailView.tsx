import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, CheckCircle, XCircle, Copy, ExternalLink } from 'lucide-react'
import {
  getApplicationForReview,
  approveAndSubmitApplication,
  rejectApplication,
} from '../api/pipeline'

interface ApplicationDetailViewProps {
  applicationId: number
  onClose: () => void
}

export function ApplicationDetailView({ applicationId, onClose }: ApplicationDetailViewProps) {
  const qc = useQueryClient()
  const [editingCoverLetter, setEditingCoverLetter] = useState<string | null>(null)
  const [copyFeedback, setCopyFeedback] = useState<'resume' | 'letter' | null>(null)

  const { data: appData, isLoading } = useQuery({
    queryKey: ['application-detail', applicationId],
    queryFn: () => getApplicationForReview(applicationId),
  })

  const approveMutation = useMutation({
    mutationFn: () => approveAndSubmitApplication(applicationId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['applications-in-review'] })
      qc.invalidateQueries({ queryKey: ['pipeline-jobs'] })
      onClose()
    },
  })

  const rejectMutation = useMutation({
    mutationFn: () => rejectApplication(applicationId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['applications-in-review'] })
      qc.invalidateQueries({ queryKey: ['pipeline-jobs'] })
      onClose()
    },
  })

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8">
          <Loader2 size={24} className="animate-spin text-blue-600" />
        </div>
      </div>
    )
  }

  if (!appData) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8">
          <p className="text-gray-600">Unable to load application</p>
        </div>
      </div>
    )
  }

  const { job, tailored_resume, tailored_cover_letter } = appData

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-800">{job.title}</h2>
            <p className="text-gray-600">{job.company}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl font-bold flex-shrink-0"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Score Card */}
          {job.score !== null && job.score !== undefined && (
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-gray-800">AI Score: {job.score}/10</h3>
                <span className={`px-3 py-1 rounded text-sm font-medium ${getScoreColor(job.score!)}`}>
                  {getScoreLabel(job.score!)}
                </span>
              </div>

              {job.score_reasoning && (
                <p className="text-sm text-gray-700 mb-3">{job.score_reasoning}</p>
              )}

              <div className="grid grid-cols-2 gap-4 text-sm">
                {job.score_strengths && job.score_strengths.length > 0 && (
                  <div>
                    <p className="font-semibold text-gray-600 mb-2">Strengths:</p>
                    <ul className="space-y-1">
                      {job.score_strengths.map((s: string, i: number) => (
                        <li key={i} className="text-gray-700 flex items-start gap-2">
                          <span className="text-green-600">✓</span>
                          <span>{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {job.score_concerns && job.score_concerns.length > 0 && (
                  <div>
                    <p className="font-semibold text-gray-600 mb-2">Concerns:</p>
                    <ul className="space-y-1">
                      {job.score_concerns.map((c: string, i: number) => (
                        <li key={i} className="text-gray-700 flex items-start gap-2">
                          <span className="text-orange-600">!</span>
                          <span>{c}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Job Details Grid */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-gray-500 text-xs font-semibold mb-1">LOCATION</p>
              <p className="text-gray-800">{job.location || 'N/A'}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs font-semibold mb-1">TYPE</p>
              <p className="text-gray-800">{(job as any).job_type || 'N/A'}</p>
            </div>
            {(job as any).salary_range && (
              <div>
                <p className="text-gray-500 text-xs font-semibold mb-1">SALARY</p>
                <p className="text-gray-800">{(job as any).salary_range}</p>
              </div>
            )}
            {(job as any).posted_date && (
              <div>
                <p className="text-gray-500 text-xs font-semibold mb-1">POSTED</p>
                <p className="text-gray-800">{(job as any).posted_date}</p>
              </div>
            )}
          </div>

          {/* Job Description & Requirements */}
          <div className="grid grid-cols-2 gap-6">
            <div>
              <h3 className="font-semibold text-gray-800 mb-2">Job Description</h3>
              <div className="bg-gray-50 p-4 rounded border border-gray-200 max-h-48 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap">
                {job.description || 'No description'}
              </div>
            </div>

            <div>
              <h3 className="font-semibold text-gray-800 mb-2">Requirements</h3>
              <div className="bg-gray-50 p-4 rounded border border-gray-200 max-h-48 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap">
                {job.requirements || 'No requirements'}
              </div>
            </div>
          </div>

          {/* Application Materials */}
          <div className="border-t pt-6">
            <h3 className="font-semibold text-gray-800 mb-4">Application Materials</h3>

            {/* Resume */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-semibold text-gray-600 uppercase">Tailored Resume</p>
                <button
                  onClick={() => {
                    if (tailored_resume?.content) {
                      navigator.clipboard.writeText(tailored_resume.content)
                      setCopyFeedback('resume')
                      setTimeout(() => setCopyFeedback(null), 2000)
                    }
                  }}
                  className="text-blue-600 hover:text-blue-700 text-xs flex items-center gap-1"
                >
                  <Copy size={12} />
                  {copyFeedback === 'resume' ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <div className="bg-white border border-gray-200 rounded p-4 max-h-40 overflow-y-auto text-xs text-gray-700 whitespace-pre-wrap font-mono">
                {tailored_resume?.content || 'Loading...'}
              </div>
            </div>

            {/* Cover Letter */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-semibold text-gray-600 uppercase">Tailored Cover Letter</p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      if (tailored_cover_letter?.content) {
                        navigator.clipboard.writeText(tailored_cover_letter.content)
                        setCopyFeedback('letter')
                        setTimeout(() => setCopyFeedback(null), 2000)
                      }
                    }}
                    className="text-blue-600 hover:text-blue-700 text-xs flex items-center gap-1"
                  >
                    <Copy size={12} />
                    {copyFeedback === 'letter' ? 'Copied!' : 'Copy'}
                  </button>
                </div>
              </div>

              {editingCoverLetter ? (
                <textarea
                  value={editingCoverLetter || ''}
                  onChange={(e) => setEditingCoverLetter(e.target.value)}
                  className="w-full h-40 text-xs border border-gray-300 rounded p-3 font-mono resize-none"
                />
              ) : (
                <div className="bg-white border border-gray-200 rounded p-4 max-h-40 overflow-y-auto text-xs text-gray-700 whitespace-pre-wrap font-mono">
                  {tailored_cover_letter?.content || 'Loading...'}
                </div>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t">
            <button
              onClick={() => rejectMutation.mutate()}
              disabled={rejectMutation.isPending || approveMutation.isPending}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-red-50 text-red-700 hover:bg-red-100 rounded-lg font-medium transition disabled:opacity-50"
            >
              {rejectMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <XCircle size={16} />}
              Reject
            </button>

            <button
              onClick={() => approveMutation.mutate()}
              disabled={rejectMutation.isPending || approveMutation.isPending}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-green-600 text-white hover:bg-green-700 rounded-lg font-medium transition disabled:opacity-50"
            >
              {approveMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
              Approve & Submit
            </button>

            {job.apply_url && (
              <a
                href={job.apply_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-3 bg-gray-100 text-gray-700 hover:bg-gray-200 rounded-lg font-medium transition"
              >
                <ExternalLink size={16} />
                View Job
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function getScoreColor(score: number): string {
  if (score >= 8) return 'bg-green-100 text-green-800'
  if (score >= 6) return 'bg-blue-100 text-blue-800'
  if (score >= 4) return 'bg-yellow-100 text-yellow-800'
  return 'bg-red-100 text-red-800'
}

function getScoreLabel(score: number): string {
  if (score >= 9) return 'Excellent Match'
  if (score >= 8) return 'Strong Match'
  if (score >= 6) return 'Good Match'
  if (score >= 4) return 'Moderate Match'
  return 'Weak Match'
}
