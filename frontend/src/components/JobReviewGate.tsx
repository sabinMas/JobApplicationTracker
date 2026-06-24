import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Edit2, CheckCircle, XCircle, ExternalLink, Copy } from 'lucide-react'
import {
  getApplicationsInReview,
  getApplicationForReview,
  approveAndSubmitApplication,
  rejectApplication,
} from '../api/pipeline'

export function JobReviewGate() {
  const qc = useQueryClient()
  const [currentAppIndex, setCurrentAppIndex] = useState(0)
  const [editingCoverLetter, setEditingCoverLetter] = useState<string | null>(null)
  const [showEditMode, setShowEditMode] = useState(false)
  const [copyFeedback, setCopyFeedback] = useState<'resume' | 'letter' | null>(null)

  // Get list of applications in review
  const { data: appsData, isLoading: appsLoading } = useQuery({
    queryKey: ['applications-in-review'],
    queryFn: () => getApplicationsInReview(50, 0),
    refetchInterval: 5000,
  })

  // Get full application data when one is selected
  const currentApp = appsData?.applications?.[currentAppIndex]
  const { data: fullAppData, isLoading: appLoading } = useQuery({
    queryKey: ['application-review', currentApp?.application_id],
    queryFn: () => (currentApp ? getApplicationForReview(currentApp.application_id) : null),
    enabled: !!currentApp,
  })

  const approveMutation = useMutation({
    mutationFn: (appId: number) => approveAndSubmitApplication(appId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['applications-in-review'] })
      qc.invalidateQueries({ queryKey: ['pipeline-jobs'] })
      if (appsData && currentAppIndex < appsData.applications.length - 1) {
        setCurrentAppIndex(currentAppIndex + 1)
      } else {
        setCurrentAppIndex(0)
      }
      setShowEditMode(false)
      setEditingCoverLetter(null)
    },
  })

  const rejectMutation = useMutation({
    mutationFn: (appId: number) => rejectApplication(appId, 'Rejected during review'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['applications-in-review'] })
      qc.invalidateQueries({ queryKey: ['pipeline-jobs'] })
      if (appsData && currentAppIndex < appsData.applications.length - 1) {
        setCurrentAppIndex(currentAppIndex + 1)
      } else {
        setCurrentAppIndex(0)
      }
      setShowEditMode(false)
      setEditingCoverLetter(null)
    },
  })

  if (appsLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 size={20} className="animate-spin text-blue-600" />
      </div>
    )
  }

  if (!appsData || appsData.applications.length === 0) {
    return (
      <div className="card p-8 text-center">
        <CheckCircle size={32} className="mx-auto text-green-600 mb-3" />
        <h3 className="text-lg font-semibold text-gray-800 mb-1">All Caught Up!</h3>
        <p className="text-gray-600">No applications waiting for review. New ones will appear as they're prepared.</p>
      </div>
    )
  }

  const totalApps = appsData.applications.length
  const progress = ((currentAppIndex + 1) / totalApps) * 100

  return (
    <div className="space-y-4">
      {/* Progress Bar */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-2xl font-bold text-gray-800">Review Gate</h2>
          <span className="text-sm text-gray-600">
            {currentAppIndex + 1} of {totalApps}
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Applications List (Quick View) */}
      {appsData.applications.length > 1 && (
        <div className="card p-3 bg-gray-50 border border-gray-200 max-h-32 overflow-y-auto">
          <p className="text-xs font-semibold text-gray-600 mb-2">Other Applications</p>
          <div className="space-y-1">
            {appsData.applications.map((app: any, idx: number) => (
              <div
                key={app.application_id}
                onClick={() => setCurrentAppIndex(idx)}
                className={`text-xs p-2 rounded cursor-pointer transition ${
                  idx === currentAppIndex
                    ? 'bg-blue-100 text-blue-900 font-medium'
                    : 'bg-white text-gray-700 hover:bg-gray-100'
                }`}
              >
                {app.job_title} @ {app.company} ({app.score}/10)
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Application Review Card */}
      {appLoading ? (
        <div className="card p-12 flex items-center justify-center">
          <Loader2 size={20} className="animate-spin text-blue-600" />
        </div>
      ) : fullAppData ? (
        <ReviewApplicationCard
          appData={fullAppData}
          isEditing={showEditMode}
          editingCoverLetter={editingCoverLetter}
          onEditingChange={setEditingCoverLetter}
          onShowEditChange={setShowEditMode}
          onCopy={() => setCopyFeedback('letter')}
          copyFeedback={copyFeedback}
          onApprove={() => approveMutation.mutate(fullAppData.application_id)}
          onReject={() => rejectMutation.mutate(fullAppData.application_id)}
          isApproving={approveMutation.isPending}
          isRejecting={rejectMutation.isPending}
        />
      ) : (
        <div className="card p-8 text-center text-gray-500">Unable to load application details</div>
      )}
    </div>
  )
}

interface ReviewApplicationCardProps {
  appData: any
  isEditing: boolean
  editingCoverLetter: string | null
  onEditingChange: (letter: string | null) => void
  onShowEditChange: (show: boolean) => void
  onCopy: () => void
  copyFeedback: string | null
  onApprove: () => void
  onReject: () => void
  isApproving: boolean
  isRejecting: boolean
}

function ReviewApplicationCard({
  appData,
  isEditing,
  editingCoverLetter,
  onEditingChange,
  onShowEditChange,
  onCopy,
  copyFeedback,
  onApprove,
  onReject,
  isApproving,
  isRejecting,
}: ReviewApplicationCardProps) {
  const { job, tailored_resume, tailored_cover_letter } = appData

  return (
    <div className="card p-6 space-y-6">
      {/* Job Header */}
      <div className="border-b pb-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-xl font-bold text-gray-800">{job.title}</h3>
            <p className="text-gray-600 font-medium">{job.company}</p>
            {job.location && <p className="text-gray-500 text-sm">{job.location}</p>}
          </div>
          {job.apply_url && (
            <a
              href={job.apply_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-blue-600 hover:text-blue-700 text-sm font-medium whitespace-nowrap"
            >
              <ExternalLink size={14} />
              View Job
            </a>
          )}
        </div>
      </div>

      {/* Score & Analysis */}
      {job.score !== null && job.score !== undefined && (
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-semibold text-gray-800">AI Score: {job.score}/10</h4>
            <span className={`px-3 py-1 rounded text-sm font-medium ${getScoreColor(job.score)}`}>
              {getScoreLabel(job.score)}
            </span>
          </div>

          {job.score_reasoning && (
            <div className="space-y-2">
              <p className="text-sm text-gray-700">{job.score_reasoning}</p>

              {job.score_strengths && job.score_strengths.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs font-semibold text-gray-600 mb-2">Why it matches:</p>
                  <ul className="space-y-1">
                    {job.score_strengths.map((strength: string, i: number) => (
                      <li key={i} className="text-xs text-gray-700 flex items-start gap-2">
                        <span className="text-green-600 font-bold">✓</span>
                        <span>{strength}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {job.score_concerns && job.score_concerns.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs font-semibold text-gray-600 mb-2">Potential concerns:</p>
                  <ul className="space-y-1">
                    {job.score_concerns.map((concern: string, i: number) => (
                      <li key={i} className="text-xs text-gray-700 flex items-start gap-2">
                        <span className="text-orange-600 font-bold">!</span>
                        <span>{concern}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Job Description & Requirements */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-3">
          <h4 className="font-semibold text-gray-800 text-sm">Job Description</h4>
          <div className="bg-gray-50 p-4 rounded border border-gray-200 max-h-64 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap">
            {job.description || 'No description provided'}
          </div>
        </div>

        <div className="space-y-3">
          <h4 className="font-semibold text-gray-800 text-sm">Requirements</h4>
          <div className="bg-gray-50 p-4 rounded border border-gray-200 max-h-64 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap">
            {job.requirements || 'No requirements provided'}
          </div>
        </div>
      </div>

      {/* Documents Section */}
      <div className="space-y-4 border-t pt-4">
        <h4 className="font-semibold text-gray-800">Your Application Materials</h4>

        {/* Resume */}
        <div className="bg-gray-50 p-4 rounded border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold text-gray-600">TAILORED RESUME</p>
            <button
              onClick={() => {
                if (tailored_resume?.content) {
                  navigator.clipboard.writeText(tailored_resume.content)
                  onCopy()
                  setTimeout(() => onCopy(), 2000)
                }
              }}
              className="text-blue-600 hover:text-blue-700 text-xs font-medium flex items-center gap-1"
            >
              <Copy size={12} />
              {copyFeedback === 'letter' ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <div className="bg-white p-3 rounded text-xs text-gray-700 max-h-48 overflow-y-auto whitespace-pre-wrap font-mono text-[11px]">
            {tailored_resume?.content || 'Resume loading...'}
          </div>
        </div>

        {/* Cover Letter */}
        <div className="bg-gray-50 p-4 rounded border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold text-gray-600">TAILORED COVER LETTER</p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  if (tailored_cover_letter?.content) {
                    navigator.clipboard.writeText(tailored_cover_letter.content)
                    onCopy()
                  }
                }}
                className="text-blue-600 hover:text-blue-700 text-xs font-medium flex items-center gap-1"
              >
                <Copy size={12} />
                Copy
              </button>
              <button
                onClick={() => {
                  onShowEditChange(!isEditing)
                  if (!isEditing && editingCoverLetter === null) {
                    onEditingChange(tailored_cover_letter?.content || '')
                  }
                }}
                className="text-blue-600 hover:text-blue-700 text-xs font-medium flex items-center gap-1"
              >
                <Edit2 size={12} />
                {isEditing ? 'Done' : 'Edit'}
              </button>
            </div>
          </div>

          {isEditing ? (
            <textarea
              value={editingCoverLetter || ''}
              onChange={(e) => onEditingChange(e.target.value)}
              className="w-full h-48 text-xs border border-gray-300 rounded p-2 font-mono resize-none"
              placeholder="Edit the cover letter here..."
            />
          ) : (
            <div className="bg-white p-3 rounded text-xs text-gray-700 max-h-48 overflow-y-auto whitespace-pre-wrap font-mono text-[11px]">
              {editingCoverLetter || tailored_cover_letter?.content || 'Cover letter loading...'}
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3 pt-4 border-t">
        <button
          onClick={onReject}
          disabled={isRejecting || isApproving}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-red-50 text-red-700 hover:bg-red-100 rounded-lg font-medium transition disabled:opacity-50"
        >
          {isRejecting ? <Loader2 size={16} className="animate-spin" /> : <XCircle size={16} />}
          Reject
        </button>

        <button
          onClick={() => onShowEditChange(!isEditing)}
          disabled={isRejecting || isApproving}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-amber-50 text-amber-700 hover:bg-amber-100 rounded-lg font-medium transition disabled:opacity-50"
        >
          <Edit2 size={16} />
          {isEditing ? 'Cancel' : 'Edit Letter'}
        </button>

        <button
          onClick={onApprove}
          disabled={isRejecting || isApproving}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-green-600 text-white hover:bg-green-700 rounded-lg font-medium transition disabled:opacity-50"
        >
          {isApproving ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
          Approve & Submit
        </button>
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
