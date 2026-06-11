import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Save, Plus, Trash2, Loader2, CheckCircle, FileText, Clock } from 'lucide-react'
import { getProfile, updateProfile, Profile, getDocuments, deleteDocument, extractProfileFromResume } from '../api/client'
import { DocumentUpload } from '../components/DocumentUpload'
import { formatDistanceToNow } from 'date-fns'

export function ProfilePage() {
  const qc = useQueryClient()
  const { data: profile, isLoading } = useQuery({ queryKey: ['profile'], queryFn: getProfile })
  const { data: documents = [] } = useQuery({ queryKey: ['documents'], queryFn: getDocuments })
  const [form, setForm] = useState<Profile>({})
  const [saved, setSaved] = useState(false)
  const [skillInput, setSkillInput] = useState('')

  useEffect(() => {
    if (profile) setForm(profile)
  }, [profile])

  const mutation = useMutation({
    mutationFn: (data: Profile) => updateProfile(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['profile'] })
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    },
  })

  const deleteMut = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['documents'] }),
  })

  const set = (field: keyof Profile) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm(f => ({ ...f, [field]: e.target.value }))

  if (isLoading) return (
    <div className="flex items-center justify-center h-64 text-gray-500">
      <Loader2 size={24} className="animate-spin" />
    </div>
  )

  const baseResumes = documents.filter(d => d.type === 'resume' && d.variant === 'base')
  const baseCoverLetters = documents.filter(d => d.type === 'cover_letter' && d.variant === 'base')
  const tailoredDocs = documents.filter(d => d.variant === 'tailored')

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Profile & Documents</h1>
          <p className="text-gray-600 text-sm mt-1">Your info powers AI tailoring, scoring, and form autofill</p>
        </div>
        <button
          className="btn-primary flex items-center gap-2"
          onClick={() => mutation.mutate(form)}
          disabled={mutation.isPending}
        >
          {saved ? <CheckCircle size={16} className="text-emerald-600" /> : <Save size={16} />}
          {mutation.isPending ? 'Saving…' : saved ? 'Saved!' : 'Save Profile'}
        </button>
      </div>

      {/* Guidance */}
      {profile && (profile.skills?.length || profile.experience?.length || profile.full_name) ? (
        <div className="card p-5 bg-emerald-50 border-emerald-300">
          <p className="text-sm text-emerald-900">
            ✅ Your profile is ready. Upload a new resume below to auto-extract and merge updated information. Edit any fields and click Save.
          </p>
        </div>
      ) : (
        <div className="card p-5 bg-amber-50 border-amber-300">
          <p className="text-sm text-amber-900">
            📝 Fill in your profile below, or upload a resume at the bottom to auto-extract your info. Claude will intelligently merge new data while preserving any manual entries.
          </p>
        </div>
      )}

      {/* Personal Info */}
      <div className="card p-5 space-y-4">
        <h3 className="font-semibold text-gray-800">Personal Information</h3>
        <div className="grid grid-cols-2 gap-3">
          {([
            ['full_name', 'Full Name', 'Jane Doe'],
            ['email', 'Email', 'jane@example.com'],
            ['phone', 'Phone', '+1 (555) 000-0000'],
            ['location', 'Location', 'San Francisco, CA'],
            ['linkedin_url', 'LinkedIn URL', 'https://linkedin.com/in/...'],
            ['github_url', 'GitHub URL', 'https://github.com/...'],
            ['portfolio_url', 'Portfolio / Website', 'https://yoursite.com'],
          ] as [keyof Profile, string, string][]).map(([key, label, placeholder]) => (
            <div key={key} className={key === 'linkedin_url' || key === 'github_url' || key === 'portfolio_url' ? 'col-span-2' : ''}>
              <label className="text-xs text-gray-600 mb-1 block">{label}</label>
              <input
                className="input"
                placeholder={placeholder}
                value={(form[key] as string) ?? ''}
                onChange={set(key)}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Summary */}
      <div className="card p-5 space-y-3">
        <h3 className="font-semibold text-gray-800">Professional Summary</h3>
        <textarea
          className="input min-h-[100px] resize-y"
          placeholder="Brief summary of your professional background and goals…"
          value={form.summary ?? ''}
          onChange={set('summary')}
        />
      </div>

      {/* Skills */}
      <div className="card p-5 space-y-3">
        <h3 className="font-semibold text-gray-800">Skills</h3>
        <div className="flex flex-wrap gap-2">
          {(form.skills ?? []).map((skill, i) => (
            <span key={i} className="flex items-center gap-1.5 bg-emerald-100 rounded-lg px-3 py-1 text-sm text-emerald-900">
              {skill}
              <button
                onClick={() => setForm(f => ({ ...f, skills: f.skills?.filter((_, idx) => idx !== i) }))}
                className="text-emerald-700 hover:text-red-600"
              >
                <Trash2 size={12} />
              </button>
            </span>
          ))}
          <input
            className="bg-parchment-100 border border-parchment-300 rounded-lg px-3 py-1 text-sm text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-brand-500 w-32"
            placeholder="+ Add skill"
            value={skillInput}
            onChange={e => setSkillInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && skillInput.trim()) {
                setForm(f => ({ ...f, skills: [...(f.skills ?? []), skillInput.trim()] }))
                setSkillInput('')
              }
            }}
          />
        </div>
      </div>

      {/* Experience */}
      <div className="card p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-800">Experience</h3>
          <button
            className="btn-ghost text-xs flex items-center gap-1"
            onClick={() => setForm(f => ({
              ...f,
              experience: [...(f.experience ?? []), { company: '', title: '', start: '', end: '', bullets: [] }]
            }))}
          >
            <Plus size={13} /> Add
          </button>
        </div>
        {(form.experience ?? []).map((exp, i) => (
          <div key={i} className="bg-parchment-100 rounded-xl p-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <input className="input text-sm" placeholder="Company" value={exp.company ?? ''}
                onChange={e => setForm(f => {
                  const ex = [...(f.experience ?? [])]
                  ex[i] = { ...ex[i], company: e.target.value }
                  return { ...f, experience: ex }
                })} />
              <input className="input text-sm" placeholder="Title" value={exp.title ?? ''}
                onChange={e => setForm(f => {
                  const ex = [...(f.experience ?? [])]
                  ex[i] = { ...ex[i], title: e.target.value }
                  return { ...f, experience: ex }
                })} />
              <input className="input text-sm" placeholder="Start (e.g. Jan 2022)" value={exp.start ?? ''}
                onChange={e => setForm(f => {
                  const ex = [...(f.experience ?? [])]
                  ex[i] = { ...ex[i], start: e.target.value }
                  return { ...f, experience: ex }
                })} />
              <input className="input text-sm" placeholder="End (or Present)" value={exp.end ?? ''}
                onChange={e => setForm(f => {
                  const ex = [...(f.experience ?? [])]
                  ex[i] = { ...ex[i], end: e.target.value }
                  return { ...f, experience: ex }
                })} />
            </div>
            <button className="text-xs text-red-600 hover:text-red-700 flex items-center gap-1"
              onClick={() => setForm(f => ({ ...f, experience: f.experience?.filter((_, idx) => idx !== i) }))}>
              <Trash2 size={11} /> Remove
            </button>
          </div>
        ))}
      </div>

      {/* Education */}
      <div className="card p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-800">Education</h3>
          <button
            className="btn-ghost text-xs flex items-center gap-1"
            onClick={() => setForm(f => ({
              ...f,
              education: [...(f.education ?? []), { school: '', degree: '', field: '', start: '', end: '' }]
            }))}
          >
            <Plus size={13} /> Add
          </button>
        </div>
        {(form.education ?? []).map((edu, i) => (
          <div key={i} className="bg-parchment-100 rounded-xl p-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <input className="input text-sm col-span-2" placeholder="School / University" value={edu.school ?? ''}
                onChange={e => setForm(f => {
                  const ed = [...(f.education ?? [])]
                  ed[i] = { ...ed[i], school: e.target.value }
                  return { ...f, education: ed }
                })} />
              <input className="input text-sm" placeholder="Degree (e.g. B.S.)" value={edu.degree ?? ''}
                onChange={e => setForm(f => {
                  const ed = [...(f.education ?? [])]
                  ed[i] = { ...ed[i], degree: e.target.value }
                  return { ...f, education: ed }
                })} />
              <input className="input text-sm" placeholder="Field of Study" value={edu.field ?? ''}
                onChange={e => setForm(f => {
                  const ed = [...(f.education ?? [])]
                  ed[i] = { ...ed[i], field: e.target.value }
                  return { ...f, education: ed }
                })} />
            </div>
            <button className="text-xs text-red-600 hover:text-red-700 flex items-center gap-1"
              onClick={() => setForm(f => ({ ...f, education: f.education?.filter((_, idx) => idx !== i) }))}>
              <Trash2 size={11} /> Remove
            </button>
          </div>
        ))}
      </div>

      {/* ═══════════════ Documents Section ═══════════════ */}
      <div className="border-t border-parchment-300 pt-8">
        <h2 className="text-xl font-bold text-gray-800 mb-1">Documents</h2>
        <p className="text-gray-600 text-sm mb-6">
          Upload your base resume and cover letter examples. AI uses them to generate tailored versions for each job.
        </p>
      </div>

      {/* Base resume upload — extracts profile data */}
      <div className="card p-5 space-y-4">
        <h3 className="font-semibold text-gray-800">Base Resume</h3>
        <p className="text-sm text-gray-600">
          Upload your master resume PDF. AI will extract your profile info and use it for tailoring.
        </p>
        <ResumeExtractUpload onExtracted={(extracted) => {
          setForm(f => ({ ...f, ...extracted }))
          qc.invalidateQueries({ queryKey: ['profile'] })
          qc.invalidateQueries({ queryKey: ['documents'] })
        }} />
        <div className="space-y-2">
          {baseResumes.map(doc => <DocRow key={doc.id} doc={doc} onDelete={() => deleteMut.mutate(doc.id)} />)}
          {baseResumes.length === 0 && (
            <p className="text-xs text-gray-600 italic">No resume uploaded yet.</p>
          )}
        </div>
      </div>

      {/* Cover letter examples */}
      <div className="card p-5 space-y-4">
        <h3 className="font-semibold text-gray-800">Cover Letter Examples</h3>
        <p className="text-sm text-gray-600">
          Upload 1–3 cover letter PDFs you're proud of. AI will match their tone and style when generating new ones.
        </p>
        <DocumentUpload docType="cover_letter" label="Cover Letter Example" />
        <div className="space-y-2">
          {baseCoverLetters.map(doc => <DocRow key={doc.id} doc={doc} onDelete={() => deleteMut.mutate(doc.id)} />)}
          {baseCoverLetters.length === 0 && (
            <p className="text-xs text-gray-600 italic">No cover letters uploaded yet.</p>
          )}
        </div>
      </div>

      {/* Generated tailored documents */}
      {tailoredDocs.length > 0 && (
        <div className="card p-5 space-y-4">
          <h3 className="font-semibold text-gray-800">
            AI-Generated Documents
            <span className="ml-2 text-xs bg-parchment-200 text-gray-600 rounded-full px-2 py-0.5">
              {tailoredDocs.length}
            </span>
          </h3>
          <div className="space-y-2">
            {tailoredDocs.map(doc => <DocRow key={doc.id} doc={doc} onDelete={() => deleteMut.mutate(doc.id)} />)}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Document row component ──────────────────────────────────────────────────

function DocRow({ doc, onDelete }: { doc: { id: number; filename: string; type: string; created_at?: string }; onDelete: () => void }) {
  return (
    <div className="flex items-center gap-3 bg-parchment-100 rounded-xl p-3">
      <FileText size={18} className={doc.type === 'resume' ? 'text-brand-600' : 'text-purple-600'} />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-800 truncate">{doc.filename}</p>
        {doc.created_at && (
          <p className="text-xs text-gray-600 flex items-center gap-1 mt-0.5">
            <Clock size={10} />
            {formatDistanceToNow(new Date(doc.created_at), { addSuffix: true })}
          </p>
        )}
      </div>
      <button
        onClick={onDelete}
        className="text-gray-600 hover:text-red-600 transition-colors p-1.5"
      >
        <Trash2 size={15} />
      </button>
    </div>
  )
}

// ─── Resume extract upload component ─────────────────────────────────────────

import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, AlertCircle } from 'lucide-react'

function ResumeExtractUpload({ onExtracted }: { onExtracted: (data: Partial<Profile>) => void }) {
  const [status, setStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle')
  const [message, setMessage] = useState('')
  const [changes, setChanges] = useState<string[]>([])
  const [extractedCount, setExtractedCount] = useState(0)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return
    setStatus('uploading')
    setMessage(`Extracting profile from ${file.name}…`)
    try {
      const result = await extractProfileFromResume(file)
      if (result.extracted && Object.keys(result.extracted).length > 0) {
        setStatus('success')
        setChanges(result.changes)
        setExtractedCount(Object.keys(result.extracted).length)

        // Use merged profile if available, otherwise extracted
        const profileToApply = result.merged || result.extracted

        if (result.changes.length > 0) {
          // Format changes for display (convert snake_case to Title Case)
          const formattedChanges = result.changes.map(field =>
            field.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
          )
          setMessage(`✅ Profile auto-saved! Updated: ${formattedChanges.join(', ')}`)
        } else {
          setMessage(`Resume uploaded. Profile merged.`)
        }
        onExtracted(profileToApply)
      } else {
        setStatus('success')
        setMessage(`Resume uploaded. No data could be auto-extracted — please fill in below.`)
        setChanges([])
        onExtracted({})
      }
      setTimeout(() => setStatus('idle'), 5000)
    } catch (error) {
      setStatus('error')
      setMessage('Upload failed. Check file format and try again.')
      setChanges([])
      setTimeout(() => setStatus('idle'), 4000)
    }
  }, [onExtracted])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled: status === 'uploading',
  })

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-brand-500 bg-brand-50'
            : status === 'success'
            ? 'border-emerald-600 bg-emerald-50'
            : status === 'error'
            ? 'border-red-600 bg-red-50'
            : 'border-parchment-300 hover:border-parchment-400 bg-parchment-100'
        }`}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-2">
          {status === 'success' ? (
            <CheckCircle size={32} className="text-emerald-600" />
          ) : status === 'error' ? (
            <AlertCircle size={32} className="text-red-600" />
          ) : status === 'uploading' ? (
            <Loader2 size={32} className="text-brand-600 animate-spin" />
          ) : (
            <div className="relative">
              <FileText size={32} className="text-parchment-400" />
              <Upload size={14} className="text-brand-600 absolute -bottom-1 -right-1" />
            </div>
          )}
          <div>
            <p className="text-sm font-medium text-gray-800">
              {status === 'idle' && !isDragActive && 'Upload Resume PDF'}
              {status === 'idle' && isDragActive && 'Drop PDF here'}
              {status !== 'idle' && message}
            </p>
            {status === 'idle' && (
              <p className="text-xs text-gray-600 mt-0.5">PDF only · Will auto-extract and merge your profile info</p>
            )}
          </div>
        </div>
      </div>

      {/* Changes feedback card */}
      {status === 'success' && changes.length > 0 && (
        <div className="bg-emerald-50 border border-emerald-300 rounded-lg p-4">
          <div className="space-y-2">
            <p className="text-sm font-medium text-emerald-900">
              ✨ Profile Auto-Updated ({changes.length} field{changes.length !== 1 ? 's' : ''})
            </p>
            <div className="flex flex-wrap gap-1">
              {changes.map(field => (
                <span key={field} className="text-xs bg-emerald-200 text-emerald-800 rounded px-2 py-1">
                  {field.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                </span>
              ))}
            </div>
            <p className="text-xs text-emerald-700 mt-2">
              Fields were intelligently merged: new data added where empty, manual entries preserved.
            </p>
          </div>
        </div>
      )}

      {/* No changes feedback card */}
      {status === 'success' && extractedCount > 0 && changes.length === 0 && (
        <div className="bg-blue-50 border border-blue-300 rounded-lg p-4">
          <p className="text-sm text-blue-900">
            ℹ️ Profile data extracted but not changed (you already have this info filled in).
          </p>
        </div>
      )}
    </div>
  )
}
