import { useState } from 'react'
import { Link2, Search, Plus, Loader2, Building2, MapPin, CheckCircle } from 'lucide-react'
import { useScrapeJob, useCreateJob } from '../hooks/useJobs'
import { getGreenhouseJobs, Job } from '../api/client'
import { useNavigate } from 'react-router-dom'

export function JobSearch() {
  const navigate = useNavigate()
  const scrapeJob = useScrapeJob()
  const createJob = useCreateJob()

  const [url, setUrl] = useState('')
  const [scraped, setScraped] = useState<Job | null>(null)

  const [ghSlug, setGhSlug] = useState('')
  const [ghJobs, setGhJobs] = useState<Job[]>([])
  const [ghLoading, setGhLoading] = useState(false)
  const [ghError, setGhError] = useState('')

  const [manualMode, setManualMode] = useState(false)
  const [manual, setManual] = useState({ title: '', company: '', location: '', apply_url: '', job_type: '' })

  const handleScrape = async () => {
    if (!url.trim()) return
    const result = await scrapeJob.mutateAsync(url.trim())
    setScraped(result)
    setUrl('')
  }

  const handleGreenhouse = async () => {
    if (!ghSlug.trim()) return
    setGhLoading(true)
    setGhError('')
    try {
      const jobs = await getGreenhouseJobs(ghSlug.trim().toLowerCase())
      setGhJobs(jobs)
    } catch {
      setGhError(`No Greenhouse board found for "${ghSlug}". Check the company's exact board slug.`)
    } finally {
      setGhLoading(false)
    }
  }

  const handleManualSubmit = async () => {
    if (!manual.title || !manual.company) return
    const job = await createJob.mutateAsync({ ...manual, source: 'manual' })
    navigate(`/jobs/${job.id}`)
  }

  const importGreenhouseJob = async (job: Job) => {
    const created = await createJob.mutateAsync(job)
    navigate(`/jobs/${created.id}`)
  }

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Add a Job</h1>
        <p className="text-gray-600 text-sm mt-1">Paste any job URL, search Greenhouse, or enter manually</p>
      </div>

      {/* ── URL Import ── */}
      <div className="card p-5 space-y-4">
        <div className="flex items-center gap-2 text-brand-600 font-semibold">
          <Link2 size={18} />
          Import from URL
        </div>
        <p className="text-sm text-gray-600">
          Paste a job URL from LinkedIn, Indeed, ZipRecruiter, Handshake, or any company website.
          AI will extract all the details automatically.
        </p>
        <div className="flex gap-2">
          <input
            className="input flex-1"
            placeholder="https://www.linkedin.com/jobs/view/..."
            value={url}
            onChange={e => setUrl(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleScrape()}
          />
          <button
            className="btn-primary flex items-center gap-2 whitespace-nowrap"
            onClick={handleScrape}
            disabled={scrapeJob.isPending || !url.trim()}
          >
            {scrapeJob.isPending ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            Import
          </button>
        </div>

        {scraped && (
          <div className="bg-emerald-50 border border-emerald-300 rounded-xl p-4 flex items-start gap-3">
            <CheckCircle size={20} className="text-emerald-700 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="font-semibold text-gray-800">{scraped.title}</p>
              <p className="text-sm text-gray-600">{scraped.company} · {scraped.location}</p>
              <p className="text-xs text-gray-500 mt-1">Saved to your tracker</p>
            </div>
            <button className="btn-primary text-sm py-1" onClick={() => navigate(`/jobs/${scraped.id}`)}>
              View
            </button>
          </div>
        )}

        {scrapeJob.isError && (
          <p className="text-red-600 text-sm">Failed to import job. Try again or use manual entry.</p>
        )}
      </div>

      {/* ── Greenhouse Search ── */}
      <div className="card p-5 space-y-4">
        <div className="flex items-center gap-2 text-emerald-700 font-semibold">
          <Building2 size={18} />
          Search Greenhouse Board
        </div>
        <p className="text-sm text-gray-600">
          Enter a company's Greenhouse board slug (e.g. <code className="text-emerald-700 bg-emerald-50 px-1 py-0.5 rounded">airbnb</code>, <code className="text-emerald-700 bg-emerald-50 px-1 py-0.5 rounded">stripe</code>) to see all open roles.
        </p>
        <div className="flex gap-2">
          <input
            className="input flex-1"
            placeholder="company-slug"
            value={ghSlug}
            onChange={e => setGhSlug(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleGreenhouse()}
          />
          <button
            className="btn-primary flex items-center gap-2"
            onClick={handleGreenhouse}
            disabled={ghLoading || !ghSlug.trim()}
          >
            {ghLoading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            Search
          </button>
        </div>
        {ghError && <p className="text-red-600 text-sm">{ghError}</p>}
        {ghJobs.length > 0 && (
          <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
            {ghJobs.map((job, i) => (
              <div key={i} className="bg-parchment-100 rounded-xl p-3 flex items-center justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-gray-800 truncate">{job.title}</p>
                  <div className="flex items-center gap-2 text-xs text-gray-600 mt-0.5">
                    <Building2 size={11} />{job.company}
                    {job.location && <><MapPin size={11} />{job.location}</>}
                  </div>
                </div>
                <button
                  className="btn-primary text-xs py-1 px-3 whitespace-nowrap"
                  onClick={() => importGreenhouseJob(job)}
                  disabled={createJob.isPending}
                >
                  + Track
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Manual Entry ── */}
      <div className="card p-5 space-y-4">
        <button
          className="flex items-center gap-2 text-gray-600 hover:text-gray-800 transition-colors w-full text-left"
          onClick={() => setManualMode(m => !m)}
        >
          <Plus size={18} />
          <span className="font-semibold">Manual Entry</span>
          <span className="text-xs text-gray-500 ml-auto">{manualMode ? '▲ Hide' : '▼ Show'}</span>
        </button>

        {manualMode && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-600 mb-1 block">Job Title *</label>
                <input className="input" placeholder="Software Engineer" value={manual.title}
                  onChange={e => setManual(m => ({ ...m, title: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs text-gray-600 mb-1 block">Company *</label>
                <input className="input" placeholder="Acme Corp" value={manual.company}
                  onChange={e => setManual(m => ({ ...m, company: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs text-gray-600 mb-1 block">Location</label>
                <input className="input" placeholder="San Francisco, CA" value={manual.location}
                  onChange={e => setManual(m => ({ ...m, location: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs text-gray-600 mb-1 block">Job Type</label>
                <select className="input" value={manual.job_type}
                  onChange={e => setManual(m => ({ ...m, job_type: e.target.value }))}>
                  <option value="">Select…</option>
                  <option value="full-time">Full-time</option>
                  <option value="internship">Internship</option>
                  <option value="part-time">Part-time</option>
                  <option value="contract">Contract</option>
                </select>
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-600 mb-1 block">Apply URL</label>
              <input className="input" placeholder="https://company.com/careers/apply" value={manual.apply_url}
                onChange={e => setManual(m => ({ ...m, apply_url: e.target.value }))} />
            </div>
            <button
              className="btn-primary w-full"
              onClick={handleManualSubmit}
              disabled={createJob.isPending || !manual.title || !manual.company}
            >
              {createJob.isPending ? 'Saving…' : 'Save Job'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
