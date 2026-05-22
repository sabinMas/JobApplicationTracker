import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, CheckCircle, AlertCircle } from 'lucide-react'
import { uploadDocument } from '../api/client'
import { useQueryClient } from '@tanstack/react-query'

interface Props {
  docType: 'resume' | 'cover_letter'
  label: string
  onUploaded?: () => void
}

export function DocumentUpload({ docType, label, onUploaded }: Props) {
  const [status, setStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle')
  const [message, setMessage] = useState('')
  const qc = useQueryClient()

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return
    setStatus('uploading')
    setMessage(`Uploading ${file.name}…`)
    try {
      await uploadDocument(file, docType)
      setStatus('success')
      setMessage(`${file.name} uploaded successfully`)
      qc.invalidateQueries({ queryKey: ['documents'] })
      onUploaded?.()
      setTimeout(() => setStatus('idle'), 3000)
    } catch {
      setStatus('error')
      setMessage('Upload failed. Please try again.')
    }
  }, [docType, qc, onUploaded])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled: status === 'uploading',
  })

  return (
    <div>
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
          ) : (
            <div className="relative">
              <FileText size={32} className="text-parchment-400" />
              <Upload size={14} className="text-brand-600 absolute -bottom-1 -right-1" />
            </div>
          )}
          <div>
            <p className="text-sm font-medium text-gray-800">
              {status === 'uploading' ? message :
               status === 'success' ? message :
               status === 'error' ? message :
               isDragActive ? 'Drop PDF here' :
               `Upload ${label}`}
            </p>
            {status === 'idle' && (
              <p className="text-xs text-gray-600 mt-0.5">PDF only · Drag & drop or click</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
