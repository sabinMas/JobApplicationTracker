import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Upload, CheckCircle, ArrowRight, Loader2, AlertCircle, FileText } from 'lucide-react'
import { getProfile, updateProfile, Profile } from '../api/client'
import { DocumentUpload } from '../components/DocumentUpload'
import { extractProfileFromResume } from '../api/client'
import { useDropzone } from 'react-dropzone'

type Step = 'resume' | 'cover_letters' | 'review'

export function Onboarding() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { data: profile } = useQuery({ queryKey: ['profile'], queryFn: getProfile })

  const [step, setStep] = useState<Step>('resume')
  const [extractedProfile, setExtractedProfile] = useState<Profile | null>(null)
  const [editingProfile, setEditingProfile] = useState<Profile>(profile ?? {})
  const [error, setError] = useState('')
  const [changes, setChanges] = useState<string[]>([])

  const extractMutation = useMutation({
    mutationFn: (file: File) => extractProfileFromResume(file),
    onSuccess: (data) => {
      setError('')
      setChanges(data.changes)
      // Use merged profile if available (which includes auto-saved updates), otherwise extracted
      const profileToUse = data.merged || data.extracted
      setExtractedProfile(profileToUse)
      setEditingProfile(profileToUse)
    },
    onError: () => {
      setError('Failed to extract profile. Try a different resume.')
    },
  })

  const saveMutation = useMutation({
    mutationFn: (data: Profile) => updateProfile(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['profile'] })
      navigate('/')
    },
  })

  const handleProfileChange = (field: keyof Profile) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setEditingProfile(p => ({ ...p, [field]: e.target.value }))

  const handleFinish = () => {
    saveMutation.mutate(editingProfile)
  }

  // Resume dropzone for Step 1
  const onResumeUploadDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    // Trigger profile extraction
    extractMutation.mutate(file)
  }, [extractMutation])

  const { getRootProps: getResumeRootProps, getInputProps: getResumeInputProps, isDragActive: isResumeDragActive } = useDropzone({
    onDrop: onResumeUploadDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled: extractMutation.isPending,
  })

  // ─── Step 1: Upload Resume ─────────────────────────────────────────────────

  if (step === 'resume') {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-brand-100 rounded-full mb-4">
            <Upload size={28} className="text-brand-700" />
          </div>
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Welcome! Let's Get Started</h1>
          <p className="text-gray-600">Upload your resume and Claude will AI-extract and auto-save your profile in seconds</p>
        </div>

        <div className="card p-8 space-y-6">
          <div>
            <h2 className="font-semibold text-gray-800 mb-3">Step 1: Upload Your Resume</h2>
            <p className="text-sm text-gray-600 mb-4">
              Upload a PDF of your resume. Our AI will extract your name, email, skills, experience, and education.
            </p>
            <div
              {...getResumeRootProps()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                isResumeDragActive
                  ? 'border-brand-500 bg-brand-50'
                  : extractedProfile
                  ? 'border-emerald-600 bg-emerald-50'
                  : error
                  ? 'border-red-600 bg-red-50'
                  : 'border-parchment-300 hover:border-parchment-400 bg-parchment-100'
              }`}
            >
              <input {...getResumeInputProps()} />
              <div className="flex flex-col items-center gap-2">
                {extractedProfile ? (
                  <CheckCircle size={32} className="text-emerald-600" />
                ) : error ? (
                  <AlertCircle size={32} className="text-red-600" />
                ) : (
                  <div className="relative">
                    <FileText size={32} className="text-parchment-400" />
                    <Upload size={14} className="text-brand-600 absolute -bottom-1 -right-1" />
                  </div>
                )}
                <div>
                  <p className="text-sm font-medium text-gray-800">
                    {extractedProfile ? 'Resume uploaded!' : error ? error : isResumeDragActive ? 'Drop PDF here' : 'Upload Resume PDF'}
                  </p>
                  {!extractedProfile && !error && (
                    <p className="text-xs text-gray-600 mt-0.5">PDF only · Drag & drop or click</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {extractMutation.isPending && (
            <div className="bg-blue-50 border border-blue-300 rounded-lg p-4 flex items-center gap-3">
              <Loader2 size={20} className="text-blue-600 animate-spin" />
              <span className="text-blue-800">AI is analyzing your resume…</span>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-300 rounded-lg p-4 flex items-center gap-3">
              <AlertCircle size={20} className="text-red-600" />
              <span className="text-red-800">{error}</span>
            </div>
          )}

          {extractedProfile && (
            <div className="bg-emerald-50 border border-emerald-300 rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-2">
                <CheckCircle size={20} className="text-emerald-700" />
                <span className="text-emerald-800 font-medium">
                  {changes.length > 0 ? '✨ Profile Auto-Saved!' : 'Profile Extracted!'}
                </span>
              </div>

              {changes.length > 0 && (
                <div className="bg-white rounded p-3 space-y-2">
                  <p className="text-sm text-gray-700 font-medium">Updated fields:</p>
                  <div className="flex flex-wrap gap-1">
                    {changes.map(field => (
                      <span key={field} className="text-xs bg-emerald-200 text-emerald-800 rounded px-2 py-1">
                        {field.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-gray-600">Name:</span>
                  <p className="text-gray-800 font-medium">{extractedProfile.full_name || '—'}</p>
                </div>
                <div>
                  <span className="text-gray-600">Email:</span>
                  <p className="text-gray-800 font-medium">{extractedProfile.email || '—'}</p>
                </div>
                <div>
                  <span className="text-gray-600">Location:</span>
                  <p className="text-gray-800 font-medium">{extractedProfile.location || '—'}</p>
                </div>
                <div>
                  <span className="text-gray-600">Skills:</span>
                  <p className="text-gray-800 font-medium">{(extractedProfile.skills?.length ?? 0) || '0'} found</p>
                </div>
              </div>
              <button
                className="btn-primary w-full flex items-center justify-center gap-2 mt-2"
                onClick={() => setStep('cover_letters')}
              >
                Next: Cover Letters
                <ArrowRight size={16} />
              </button>
            </div>
          )}

          {!extractedProfile && (
            <p className="text-center text-gray-500 text-sm italic">Upload your resume to continue</p>
          )}
        </div>
      </div>
    )
  }

  // ─── Step 2: Upload Cover Letters ──────────────────────────────────────────

  if (step === 'cover_letters') {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-brand-100 rounded-full mb-4">
            <CheckCircle size={28} className="text-brand-700" />
          </div>
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Add Cover Letter Examples</h1>
          <p className="text-gray-600">Optional: Upload 1-3 examples so AI can match your writing style</p>
        </div>

        <div className="card p-8 space-y-6">
          <div>
            <h2 className="font-semibold text-gray-800 mb-3">Step 2: Cover Letter Examples</h2>
            <p className="text-sm text-gray-600 mb-4">
              Upload PDFs of cover letters you're proud of. AI will use them to learn your tone and structure when generating new ones.
              <strong className="text-gray-700 block mt-1">You can skip this and add them later.</strong>
            </p>
            <DocumentUpload
              docType="cover_letter"
              label="Cover Letter Example (Optional)"
              onUploaded={() => {}}
            />
          </div>

          <div className="flex gap-3">
            <button
              className="btn-secondary flex-1 flex items-center justify-center gap-2"
              onClick={() => setStep('review')}
            >
              Skip
            </button>
            <button
              className="btn-primary flex-1 flex items-center justify-center gap-2"
              onClick={() => setStep('review')}
            >
              Next: Review
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ─── Step 3: Review Profile ───────────────────────────────────────────────

  if (step === 'review') {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-emerald-100 rounded-full mb-4">
            <CheckCircle size={28} className="text-emerald-700" />
          </div>
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Review Your Profile</h1>
          <p className="text-gray-600">Edit any fields before we lock in your profile</p>
        </div>

        <div className="space-y-6">
          {/* Personal Info */}
          <div className="card p-5 space-y-4">
            <h3 className="font-semibold text-gray-800">Personal Information</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-600 mb-1 block">Full Name</label>
                <input
                  className="input text-sm"
                  value={editingProfile.full_name ?? ''}
                  onChange={handleProfileChange('full_name')}
                />
              </div>
              <div>
                <label className="text-xs text-gray-600 mb-1 block">Email</label>
                <input
                  className="input text-sm"
                  value={editingProfile.email ?? ''}
                  onChange={handleProfileChange('email')}
                />
              </div>
              <div>
                <label className="text-xs text-gray-600 mb-1 block">Phone</label>
                <input
                  className="input text-sm"
                  value={editingProfile.phone ?? ''}
                  onChange={handleProfileChange('phone')}
                />
              </div>
              <div>
                <label className="text-xs text-gray-600 mb-1 block">Location</label>
                <input
                  className="input text-sm"
                  value={editingProfile.location ?? ''}
                  onChange={handleProfileChange('location')}
                />
              </div>
            </div>
          </div>

          {/* Summary */}
          <div className="card p-5 space-y-3">
            <h3 className="font-semibold text-gray-800">Professional Summary</h3>
            <textarea
              className="input min-h-[80px] resize-y text-sm"
              value={editingProfile.summary ?? ''}
              onChange={handleProfileChange('summary')}
            />
          </div>

          {/* Skills */}
          {editingProfile.skills && editingProfile.skills.length > 0 && (
            <div className="card p-5 space-y-3">
              <h3 className="font-semibold text-gray-800">Skills ({editingProfile.skills.length})</h3>
              <div className="flex flex-wrap gap-2">
                {editingProfile.skills.map((s, i) => (
                  <span key={i} className="badge bg-emerald-100 text-emerald-800 text-xs px-2 py-0.5">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Experience */}
          {editingProfile.experience && editingProfile.experience.length > 0 && (
            <div className="card p-5 space-y-3">
              <h3 className="font-semibold text-gray-800">Experience ({editingProfile.experience.length} roles)</h3>
              <div className="space-y-2 text-sm">
                {editingProfile.experience.map((exp, i) => (
                  <div key={i} className="bg-parchment-100 rounded p-2">
                    <p className="text-gray-800 font-medium">{exp.title}</p>
                    <p className="text-gray-600">{exp.company}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Education */}
          {editingProfile.education && editingProfile.education.length > 0 && (
            <div className="card p-5 space-y-3">
              <h3 className="font-semibold text-gray-800">Education ({editingProfile.education.length})</h3>
              <div className="space-y-2 text-sm">
                {editingProfile.education.map((edu, i) => (
                  <div key={i} className="bg-parchment-100 rounded p-2">
                    <p className="text-gray-800 font-medium">{edu.school}</p>
                    <p className="text-gray-600">{edu.degree}{edu.field ? ` in ${edu.field}` : ''}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-3">
            <button
              className="btn-secondary flex-1"
              onClick={() => setStep('cover_letters')}
            >
              Back
            </button>
            <button
              className="btn-primary flex-1 flex items-center justify-center gap-2"
              onClick={handleFinish}
              disabled={saveMutation.isPending}
            >
              {saveMutation.isPending ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Saving…
                </>
              ) : (
                <>
                  <CheckCircle size={16} />
                  Looks Good, Let's Go!
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    )
  }

  return null
}
