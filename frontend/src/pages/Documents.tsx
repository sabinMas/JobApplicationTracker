import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getDocuments, deleteDocument } from '../api/client'
import { DocumentUpload } from '../components/DocumentUpload'
import { FileText, Download, Trash2, Clock } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export function Documents() {
  const qc = useQueryClient()
  const { data: documents = [] } = useQuery({ queryKey: ['documents'], queryFn: getDocuments })
  const deleteMut = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['documents'] }),
  })

  const baseResumes = documents.filter(d => d.type === 'resume' && d.variant === 'base')
  const baseCoverLetters = documents.filter(d => d.type === 'cover_letter' && d.variant === 'base')
  const tailoredDocs = documents.filter(d => d.variant === 'tailored')

  const DocRow = ({ doc }: { doc: typeof documents[0] }) => (
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
      <a
        href={`/api/documents/${doc.id}/download`}
        target="_blank"
        className="text-gray-500 hover:text-brand-600 transition-colors p-1.5"
      >
        <Download size={15} />
      </a>
      <button
        onClick={() => deleteMut.mutate(doc.id)}
        className="text-gray-600 hover:text-red-600 transition-colors p-1.5"
      >
        <Trash2 size={15} />
      </button>
    </div>
  )

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Documents</h1>
        <p className="text-gray-600 text-sm mt-1">
          Upload your base resume and cover letter examples. AI uses them to generate tailored versions for each job.
        </p>
      </div>

      {/* Base resume upload */}
      <div className="card p-5 space-y-4">
        <h3 className="font-semibold text-gray-800">Base Resume</h3>
        <p className="text-sm text-gray-600">
          Upload your master resume PDF. AI will use it as the foundation for all tailored versions.
        </p>
        <DocumentUpload docType="resume" label="Base Resume" />
        <div className="space-y-2">
          {baseResumes.map(doc => <DocRow key={doc.id} doc={doc} />)}
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
          {baseCoverLetters.map(doc => <DocRow key={doc.id} doc={doc} />)}
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
            {tailoredDocs.map(doc => <DocRow key={doc.id} doc={doc} />)}
          </div>
        </div>
      )}
    </div>
  )
}
