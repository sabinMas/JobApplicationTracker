import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Edit2, CheckCircle, XCircle } from 'lucide-react'
import { getJobsForReview, reviewJob } from '../api/pipeline'

export function JobReviewGate() {
  const qc = useQueryClient()
  const [currentJobIndex, setCurrentJobIndex] = useState(0)
  const [editingCoverLetter, setEditingCoverLetter] = useState<string | null>(null)
  const [showEditMode, setShowEditMode] = useState(false)

  const { data: jobsData, isLoading } = useQuery({
    queryKey: ['jobs-for-review'],
    queryFn: () => getJobsForReview(0, 50),
    refetchInterval: 5000, // Refresh every 5 seconds
  })

  const reviewMutation = useMutation({
    mutationFn: (action: { job_id: number; action: 'approve' | 'reject' | 'edit'; edited_cover_letter?: string }) =>
      reviewJob(action.job_id, action.action, action.edited_cover_letter),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['jobs-for-review'] })
      // Move to next job
      if (jobsData && currentJobIndex < jobsData.length - 1) {
        setCurrentJobIndex(currentJobIndex + 1)
      } else {
        setCurrentJobIndex(0)
      }
      setShowEditMode(false)
      setEditingCoverLetter(null)
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 size={20} className="animate-spin text-blue-600" />
      </div>
    )
  }

  if (!jobsData || jobsData.length === 0) {
    return (
      <div className="card p-8 text-center">
        <CheckCircle size={32} className="mx-auto text-green-600 mb-3" />
        <h3 className="text-lg font-semibold text-gray-800 mb-1">All Caught Up!</h3>
        <p className="text-gray-600">No jobs waiting for review. New ones will appear as they're discovered.</p>
      </div>
    )
  }

  const currentJob = jobsData[currentJobIndex]
  const totalJobs = jobsData.length
  const progress = ((currentJobIndex + 1) / totalJobs) * 100

  return (
    <div className="space-y-4">
      {/* Progress Bar */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-2xl font-bold text-gray-800">Review Gate</h2>
          <span className="text-sm text-gray-600">
            {currentJobIndex + 1} of {totalJobs}
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Job Review Card */}
      <div className="card p-6 space-y-6">
        {/* Job Header */}
        <div className="border-b pb-4">
          <h3 className="text-xl font-bold text-gray-800">{currentJob.title}</h3>
          <p className="text-gray-600 font-medium">{currentJob.company}</p>
          {currentJob.location && <p className="text-gray-500 text-sm">{currentJob.location}</p>}
        </div>

        {/* Job Score & Analysis */}
        {currentJob.score !== null && currentJob.score !== undefined && (
          <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold text-gray-800">AI Score: {currentJob.score}/10</h4>
              <span className={`px-3 py-1 rounded text-sm font-medium ${getScoreColor(currentJob.score)}`}>
                {getScoreLabel(currentJob.score)}
              </span>
            </div>

            {currentJob.score_reasoning && (
              <div className="space-y-2">
                <p className="text-sm text-gray-700">{currentJob.score_reasoning}</p>

                {currentJob.score_strengths && currentJob.score_strengths.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold text-gray-600 mb-2">Why it matches:</p>
                    <ul className="space-y-1">
                      {currentJob.score_strengths.map((strength, i) => (
                        <li key={i} className="text-xs text-gray-700 flex items-start gap-2">
                          <span className="text-green-600 font-bold">✓</span>
                          <span>{strength}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {currentJob.score_concerns && currentJob.score_concerns.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold text-gray-600 mb-2">Potential concerns:</p>
                    <ul className="space-y-1">
                      {currentJob.score_concerns.map((concern, i) => (
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

        {/* Two Column Layout: Job Details + Documents */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Left: Job Details */}
          <div className="space-y-3">
            <h4 className="font-semibold text-gray-800 text-sm">Job Details</h4>
            {currentJob.apply_url && (
              <div>
                <a
                  href={currentJob.apply_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-700 text-sm font-medium break-all"
                >
                  View full posting →
                </a>
              </div>
            )}
            {currentJob.enrichment_data && (
              <div className="bg-gray-50 p-3 rounded border border-gray-200">
                <p className="text-xs font-semibold text-gray-600 mb-2">AI Enrichment</p>
                <p className="text-sm text-gray-700 line-clamp-4">{currentJob.enrichment_data}</p>
              </div>
            )}
          </div>

          {/* Right: Your Documents */}
          <div className="space-y-3">
            <h4 className="font-semibold text-gray-800 text-sm">Your Application Materials</h4>

            {/* Resume Preview */}
            <div className="bg-gray-50 p-3 rounded border border-gray-200">
              <p className="text-xs font-semibold text-gray-600 mb-2">Resume</p>
              <p className="text-xs text-gray-600">
                Your tailored resume will be used for this application.
              </p>
            </div>

            {/* Cover Letter */}
            <div className="bg-gray-50 p-3 rounded border border-gray-200">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-semibold text-gray-600">Cover Letter</p>
                <button
                  onClick={() => {
                    setShowEditMode(!showEditMode)
                    if (!showEditMode) {
                      setEditingCoverLetter(
                        editingCoverLetter ||
                          currentJob.pipeline_data?.generated_cover_letter ||
                          'Generated cover letter will appear here...'
                      )
                    }
                  }}
                  className="text-blue-600 hover:text-blue-700 text-xs font-medium flex items-center gap-1"
                >
                  <Edit2 size={12} />
                  {showEditMode ? 'Done' : 'Edit'}
                </button>
              </div>

              {showEditMode ? (
                <textarea
                  value={editingCoverLetter || ''}
                  onChange={(e) => setEditingCoverLetter(e.target.value)}
                  className="w-full h-32 text-xs border border-gray-300 rounded p-2 font-mono resize-none"
                  placeholder="Edit the cover letter here..."
                />
              ) : (
                <p className="text-xs text-gray-700 line-clamp-4">
                  {editingCoverLetter || currentJob.pipeline_data?.generated_cover_letter || 'No cover letter generated yet'}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-4 border-t">
          <button
            onClick={() =>
              reviewMutation.mutate({
                job_id: currentJob.id,
                action: 'reject',
              })
            }
            disabled={reviewMutation.isPending}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-red-50 text-red-700 hover:bg-red-100 rounded-lg font-medium transition disabled:opacity-50"
          >
            {reviewMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <XCircle size={16} />}
            Skip
          </button>

          <button
            onClick={() => {
              setShowEditMode(!showEditMode)
            }}
            disabled={reviewMutation.isPending}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-amber-50 text-amber-700 hover:bg-amber-100 rounded-lg font-medium transition disabled:opacity-50"
          >
            <Edit2 size={16} />
            {showEditMode ? 'Cancel Edit' : 'Review & Edit'}
          </button>

          <button
            onClick={() => {
              if (showEditMode && editingCoverLetter) {
                reviewMutation.mutate({
                  job_id: currentJob.id,
                  action: 'edit',
                  edited_cover_letter: editingCoverLetter,
                })
              } else {
                reviewMutation.mutate({
                  job_id: currentJob.id,
                  action: 'approve',
                })
              }
            }}
            disabled={reviewMutation.isPending}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-green-600 text-white hover:bg-green-700 rounded-lg font-medium transition disabled:opacity-50"
          >
            {reviewMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
            {showEditMode ? 'Submit with Changes' : 'Approve & Submit'}
          </button>
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
