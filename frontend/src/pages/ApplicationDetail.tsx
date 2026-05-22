import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ExternalLink, Bot, Loader2, FileText, Download,
  ArrowLeft, Pencil, CheckCircle, Trash2
} from 'lucide-react'
import {
  api, tailorDocuments, startAutomation, createApplication,
  updateApplication, deleteJob,
} from '../api/client'
import { StatusBadge } from '../components/StatusBadge'
import { AutomationPanel } from '../components/AutomationPanel'

const APP_STATUSES = [
  'pending', 'applied', 'in_review', 'phone_screen', 'interview', 'offer', 'rejected', 'withdrawn'
]

export function ApplicationDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const jobId = parseInt(id!)

  const [sessionId, setSessionId] = useState<string | null>(null)
  const [tailoring, setTailoring] = useState(false)
  const [atsUrl, setAtsUrl] = useState('')
  const [editingAts, setEditingAts] = useState(false)

  const { data: job, isLoading: jobLoading } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => api.get(`/jobs/${jobId}`).then(r => r.data),
  })

  const { data: applications = [] } = useQuery({
    queryKey: ['applications'],
    queryFn: () => api.get('/applications').then(r => r.data),
  })

  const { data: documents = [] } = useQuery({
    queryKey: ['documents'],
    queryFn: () => api.get('/documents').then(r => r.data),
  })

  const application = applications.find((a: { job_id: number }) => a.job_id === jobId)

  const tailoredResume = documents.find((d: { id: number }) => d.id === application?.tailored_resume_id)
  const tailoredCL = documents.find((d: { id: number }) => d.id === application?.tailored_cover_letter_id)

  const handleTailor = async () => {
    setTailoring(true)
    try {
      const result = await tailorDocuments(jobId)
      // Create application if not exists
      let app = application
      if (!app) {
        app = await createApplication({ job_id: jobId })
      }
      await updateApplication(app.id, {
        tailored_resume_id: result.resume_document_id,
        tailored_cover_letter_id: result.cover_letter_document_id,
      })
      qc.invalidateQueries({ queryKey: ['applications'] })
      qc.invalidateQueries({ queryKey: ['documents'] })
    } catch (e) {
      alert('Tailoring failed. Make sure you have a profile and base resume uploaded.')
    } finally {
      setTailoring(false)
    }
  }

  const handleAutoApply = async () => {
    if (!application) {
      alert('Please tailor documents first to create an application record.')
      return
    }
    const session = await startAutomation(application.id)
    setSessionId(session.session_id)
  }

  const handleUpdateStatus = async (status: string) => {
    if (!application) return
    await updateApplication(application.id, { status })
    qc.invalidateQueries({ queryKey: ['applications'] })
  }

  const handleSaveAtsUrl = async () => {
    if (!application) return
    await updateApplication(application.id, { ats_tracking_url: atsUrl })
    qc.invalidateQueries({ queryKey: ['applications'] })
    setEditingAts(false)
  }

  if (jobLoading) return (
    <div className="flex items-center justify-center h-64 text-gray-600">
      <Loader2 size={24} className="animate-spin" />
    </div>
  )
  if (!job) return <div className="text-red-400">Job not found.</div>

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Back + title */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Link to="/" className="btn-ghost p-2 mt-1">
            <ArrowLeft size={18} />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-white">{job.title}</h1>
            <p className="text-gray-400 mt-0.5">{job.company} · {job.location}</p>
            <div className="flex items-center gap-2 mt-2">
              <StatusBadge status={job.status} />
              {application && <StatusBadge status={application.status} />}
              {job.source && (
                <span className="badge bg-gray-800 text-gray-400">{job.source}</span>
              )}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          {job.apply_url && (
            <a href={job.apply_url} target="_blank" rel="noreferrer" className="btn-secondary flex items-center gap-2">
              <ExternalLink size={15} />
              Open Job
            </a>
          )}
          <button
            className="btn-primary flex items-center gap-2"
            onClick={handleAutoApply}
            disabled={!job.apply_url}
          >
            <Bot size={15} />
            Auto-Apply
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: job details */}
        <div className="lg:col-span-2 space-y-4">
          {job.description && (
            <div className="card p-4">
              <h3 className="font-semibold text-gray-300 mb-3">Job Description</h3>
              <div className="text-sm text-gray-400 whitespace-pre-wrap leading-relaxed max-h-96 overflow-y-auto">
                {job.description}
              </div>
            </div>
          )}
          {job.requirements && (
            <div className="card p-4">
              <h3 className="font-semibold text-gray-300 mb-3">Requirements</h3>
              <div className="text-sm text-gray-400 whitespace-pre-wrap leading-relaxed max-h-64 overflow-y-auto">
                {job.requirements}
              </div>
            </div>
          )}
        </div>

        {/* Right: actions + docs */}
        <div className="space-y-4">
          {/* AI Tailoring */}
          <div className="card p-4 space-y-3">
            <h3 className="font-semibold text-gray-300">AI Documents</h3>
            <button
              className="btn-primary w-full flex items-center justify-center gap-2"
              onClick={handleTailor}
              disabled={tailoring}
            >
              {tailoring ? <Loader2 size={15} className="animate-spin" /> : <Bot size={15} />}
              {tailoring ? 'Generating…' : 'Tailor Resume + Cover Letter'}
            </button>

            {tailoredResume && (
              <a
                href={`/api/documents/${tailoredResume.id}/download`}
                target="_blank"
                className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 rounded-lg p-3 transition-colors"
              >
                <FileText size={16} className="text-brand-400" />
                <span className="text-sm flex-1 truncate">{tailoredResume.filename}</span>
                <Download size={14} className="text-gray-500" />
              </a>
            )}

            {tailoredCL && (
              <a
                href={`/api/documents/${tailoredCL.id}/download`}
                target="_blank"
                className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 rounded-lg p-3 transition-colors"
              >
                <FileText size={16} className="text-purple-400" />
                <span className="text-sm flex-1 truncate">{tailoredCL.filename}</span>
                <Download size={14} className="text-gray-500" />
              </a>
            )}
          </div>

          {/* Application status */}
          {application && (
            <div className="card p-4 space-y-3">
              <h3 className="font-semibold text-gray-300">Application Status</h3>
              <div className="grid grid-cols-2 gap-1.5">
                {APP_STATUSES.map(s => (
                  <button
                    key={s}
                    onClick={() => handleUpdateStatus(s)}
                    className={`text-xs py-1.5 px-2 rounded-lg border transition-colors ${
                      application.status === s
                        ? 'border-brand-500 bg-brand-900/50 text-brand-300'
                        : 'border-gray-700 hover:border-gray-600 text-gray-500 hover:text-gray-300'
                    }`}
                  >
                    {s.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ATS Tracking URL */}
          {application && (
            <div className="card p-4 space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gray-300">ATS Tracking Link</h3>
                <button onClick={() => setEditingAts(e => !e)} className="btn-ghost p-1">
                  <Pencil size={13} />
                </button>
              </div>
              {editingAts ? (
                <div className="flex gap-2">
                  <input
                    className="input text-sm flex-1"
                    placeholder="https://company.greenhouse.io/..."
                    value={atsUrl || application.ats_tracking_url || ''}
                    onChange={e => setAtsUrl(e.target.value)}
                  />
                  <button className="btn-primary px-3 py-1" onClick={handleSaveAtsUrl}>
                    <CheckCircle size={14} />
                  </button>
                </div>
              ) : application.ats_tracking_url ? (
                <a
                  href={application.ats_tracking_url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-2 text-sm text-brand-400 hover:text-brand-300 truncate"
                >
                  <ExternalLink size={14} />
                  Track Application Status
                </a>
              ) : (
                <p className="text-xs text-gray-600">No tracking URL yet. Add one after applying.</p>
              )}
            </div>
          )}

          {/* Quick links */}
          <div className="flex gap-2">
            <button
              onClick={async () => {
                if (confirm('Delete this job?')) {
                  await deleteJob(jobId)
                  navigate('/')
                }
              }}
              className="btn-ghost flex-1 text-red-500 hover:text-red-400 flex items-center justify-center gap-1.5 text-sm"
            >
              <Trash2 size={14} />
              Delete
            </button>
          </div>
        </div>
      </div>

      {/* Automation modal */}
      {sessionId && (
        <AutomationPanel
          sessionId={sessionId}
          applicationId={application?.id ?? 0}
          onClose={() => setSessionId(null)}
        />
      )}
    </div>
  )
}
