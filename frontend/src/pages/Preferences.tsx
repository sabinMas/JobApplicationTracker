import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Save, Sparkles, Loader2, CheckCircle, Trash2, Plus } from 'lucide-react'
import {
  getPreferences,
  updatePreferences,
  seedPreferences,
  SearchPreferences,
} from '../api/preferences'

export function PreferencesPage() {
  const qc = useQueryClient()
  const { data: prefs, isLoading } = useQuery({
    queryKey: ['preferences'],
    queryFn: getPreferences,
  })
  const [form, setForm] = useState<Partial<SearchPreferences>>({})
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (prefs) setForm(prefs)
  }, [prefs])

  const saveMutation = useMutation({
    mutationFn: updatePreferences,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['preferences'] })
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    },
  })

  const seedMutation = useMutation({
    mutationFn: seedPreferences,
    onSuccess: (data) => {
      setForm(data)
      qc.invalidateQueries({ queryKey: ['preferences'] })
    },
  })

  if (isLoading)
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <Loader2 size={24} className="animate-spin" />
      </div>
    )

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Search Preferences</h1>
          <p className="text-gray-600 text-sm mt-1">
            Define what jobs to target — the pipeline uses these to score and filter
          </p>
        </div>
        <div className="flex gap-2">
          <button
            className="btn-ghost flex items-center gap-2 text-sm"
            onClick={() => seedMutation.mutate()}
            disabled={seedMutation.isPending}
          >
            {seedMutation.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Sparkles size={14} />
            )}
            AI Suggest
          </button>
          <button
            className="btn-primary flex items-center gap-2"
            onClick={() => saveMutation.mutate(form)}
            disabled={saveMutation.isPending}
          >
            {saved ? <CheckCircle size={16} className="text-emerald-600" /> : <Save size={16} />}
            {saveMutation.isPending ? 'Saving…' : saved ? 'Saved!' : 'Save'}
          </button>
        </div>
      </div>

      {/* Target Roles */}
      <TagSection
        title="Target Roles"
        description="Job titles you're looking for"
        tags={form.target_roles ?? []}
        onChange={(v) => setForm((f) => ({ ...f, target_roles: v }))}
        placeholder="e.g. Backend Engineer"
      />

      {/* Niches */}
      <TagSection
        title="Niches"
        description="Industry/domain specializations"
        tags={form.niches ?? []}
        onChange={(v) => setForm((f) => ({ ...f, niches: v }))}
        placeholder="e.g. FinTech"
      />

      {/* Must-Have Keywords */}
      <TagSection
        title="Must-Have Keywords"
        description="Jobs must mention at least one of these"
        tags={form.must_have_keywords ?? []}
        onChange={(v) => setForm((f) => ({ ...f, must_have_keywords: v }))}
        placeholder="e.g. Python"
      />

      {/* Avoid Keywords */}
      <TagSection
        title="Avoid Keywords"
        description="Skip jobs that mention these"
        tags={form.avoid_keywords ?? []}
        onChange={(v) => setForm((f) => ({ ...f, avoid_keywords: v }))}
        placeholder="e.g. PHP"
        color="red"
      />

      {/* Locations */}
      <TagSection
        title="Locations"
        description="Preferred locations"
        tags={form.locations ?? []}
        onChange={(v) => setForm((f) => ({ ...f, locations: v }))}
        placeholder="e.g. Remote"
      />

      {/* Job Types */}
      <TagSection
        title="Job Types"
        description="full-time, part-time, contract, internship"
        tags={form.job_types ?? []}
        onChange={(v) => setForm((f) => ({ ...f, job_types: v }))}
        placeholder="e.g. full-time"
      />

      {/* Numeric / Toggle Settings */}
      <div className="card p-5 space-y-4">
        <h3 className="font-semibold text-gray-800">Automation Settings</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-gray-600 mb-1 block">Salary Floor (USD)</label>
            <input
              type="number"
              className="input"
              placeholder="80000"
              value={form.salary_floor ?? ''}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  salary_floor: e.target.value ? parseInt(e.target.value) : undefined,
                }))
              }
            />
          </div>
          <div>
            <label className="text-xs text-gray-600 mb-1 block">Seniority</label>
            <select
              className="input"
              value={form.seniority ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, seniority: e.target.value || undefined }))}
            >
              <option value="">Any</option>
              <option value="junior">Junior</option>
              <option value="mid">Mid-level</option>
              <option value="senior">Senior</option>
              <option value="lead">Lead / Staff</option>
              <option value="principal">Principal</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-600 mb-1 block">Min Score to Auto-Apply</label>
            <input
              type="number"
              className="input"
              min={1}
              max={10}
              placeholder="8"
              value={form.min_score_to_apply ?? ''}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  min_score_to_apply: e.target.value ? parseInt(e.target.value) : undefined,
                }))
              }
            />
          </div>
          <div>
            <label className="text-xs text-gray-600 mb-1 block">Daily Application Limit</label>
            <input
              type="number"
              className="input"
              min={1}
              max={50}
              placeholder="10"
              value={form.daily_application_limit ?? ''}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  daily_application_limit: e.target.value ? parseInt(e.target.value) : undefined,
                }))
              }
            />
          </div>
        </div>
        <div className="flex items-center gap-3 pt-2">
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              className="sr-only peer"
              checked={form.auto_submit_enabled ?? false}
              onChange={(e) => setForm((f) => ({ ...f, auto_submit_enabled: e.target.checked }))}
            />
            <div className="w-9 h-5 bg-gray-300 rounded-full peer-checked:bg-brand-600 after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-full" />
          </label>
          <div>
            <span className="text-sm text-gray-800 font-medium">Auto-Submit</span>
            <p className="text-xs text-gray-500">
              Automatically submit applications for jobs scoring above threshold
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              className="sr-only peer"
              checked={form.remote_ok ?? true}
              onChange={(e) => setForm((f) => ({ ...f, remote_ok: e.target.checked }))}
            />
            <div className="w-9 h-5 bg-gray-300 rounded-full peer-checked:bg-brand-600 after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-full" />
          </label>
          <span className="text-sm text-gray-800 font-medium">Remote OK</span>
        </div>
      </div>
    </div>
  )
}

// ─── Reusable Tag Section ────────────────────────────────────────────────────

function TagSection({
  title,
  description,
  tags,
  onChange,
  placeholder,
  color = 'emerald',
}: {
  title: string
  description: string
  tags: string[]
  onChange: (tags: string[]) => void
  placeholder: string
  color?: 'emerald' | 'red'
}) {
  const [input, setInput] = useState('')
  const bgClass = color === 'red' ? 'bg-red-100 text-red-900' : 'bg-emerald-100 text-emerald-900'
  const btnClass = color === 'red' ? 'text-red-700 hover:text-red-900' : 'text-emerald-700 hover:text-red-600'

  return (
    <div className="card p-5 space-y-3">
      <div>
        <h3 className="font-semibold text-gray-800">{title}</h3>
        <p className="text-xs text-gray-500">{description}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {tags.map((tag, i) => (
          <span key={i} className={`flex items-center gap-1.5 rounded-lg px-3 py-1 text-sm ${bgClass}`}>
            {tag}
            <button onClick={() => onChange(tags.filter((_, idx) => idx !== i))} className={btnClass}>
              <Trash2 size={12} />
            </button>
          </span>
        ))}
        <div className="flex items-center gap-1">
          <input
            className="bg-parchment-100 border border-parchment-300 rounded-lg px-3 py-1 text-sm text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-brand-500 w-40"
            placeholder={placeholder}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && input.trim()) {
                onChange([...tags, input.trim()])
                setInput('')
              }
            }}
          />
          <button
            className="p-1 text-gray-400 hover:text-brand-600"
            onClick={() => {
              if (input.trim()) {
                onChange([...tags, input.trim()])
                setInput('')
              }
            }}
          >
            <Plus size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}
