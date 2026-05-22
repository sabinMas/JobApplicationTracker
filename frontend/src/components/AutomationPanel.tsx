import { useState } from 'react'
import { Play, Pause, Square, Upload, FormInput, Monitor } from 'lucide-react'
import { useAutomationWebSocket } from '../hooks/useWebSocket'
import { pauseAutomation, resumeAutomation, stopAutomation, fillForm, uploadDocs } from '../api/client'
import { StatusBadge } from './StatusBadge'
import { formatDistanceToNow } from 'date-fns'

interface Props {
  sessionId: string
  applicationId: number
  onClose: () => void
}

export function AutomationPanel({ sessionId, applicationId, onClose }: Props) {
  const { events, latestScreenshot, connected } = useAutomationWebSocket(sessionId)
  const [isPaused, setIsPaused] = useState(false)
  const [loading, setLoading] = useState<string | null>(null)

  const latestStatus = events.length > 0 ? events[events.length - 1].status : 'running'

  const handle = async (action: () => Promise<unknown>, key: string) => {
    setLoading(key)
    try { await action() } finally { setLoading(null) }
  }

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="card w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <Monitor size={20} className="text-brand-400" />
            <div>
              <h2 className="font-semibold text-white">Automation Control</h2>
              <div className="flex items-center gap-2 mt-0.5">
                <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400 animate-pulse' : 'bg-gray-600'}`} />
                <span className="text-xs text-gray-500">
                  {connected ? 'Connected' : 'Disconnected'} · Session {sessionId.slice(0, 8)}
                </span>
                <StatusBadge status={latestStatus} size="sm" />
              </div>
            </div>
          </div>
          <button onClick={onClose} className="btn-ghost text-sm">Close</button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Screenshot pane */}
          <div className="flex-1 bg-gray-950 flex items-center justify-center relative overflow-hidden">
            {latestScreenshot ? (
              <img
                src={`data:image/jpeg;base64,${latestScreenshot}`}
                alt="Browser preview"
                className="max-w-full max-h-full object-contain"
              />
            ) : (
              <div className="text-gray-600 text-sm flex flex-col items-center gap-2">
                <Monitor size={40} />
                <span>Waiting for screenshot…</span>
              </div>
            )}
          </div>

          {/* Side panel: controls + log */}
          <div className="w-80 flex flex-col border-l border-gray-800">
            {/* Action buttons */}
            <div className="p-3 border-b border-gray-800 space-y-2">
              <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-2">Actions</p>

              <button
                className="btn-primary w-full flex items-center justify-center gap-2 text-sm"
                disabled={loading === 'fill'}
                onClick={() => handle(() => fillForm(sessionId), 'fill')}
              >
                <FormInput size={15} />
                {loading === 'fill' ? 'Filling…' : 'AI Fill Form'}
              </button>

              <button
                className="btn-secondary w-full flex items-center justify-center gap-2 text-sm"
                disabled={loading === 'upload'}
                onClick={() => handle(() => uploadDocs(sessionId, applicationId), 'upload')}
              >
                <Upload size={15} />
                {loading === 'upload' ? 'Uploading…' : 'Upload Documents'}
              </button>

              <div className="flex gap-2">
                <button
                  className="btn-secondary flex-1 flex items-center justify-center gap-1.5 text-sm"
                  onClick={() => {
                    if (isPaused) {
                      handle(() => resumeAutomation(sessionId), 'resume')
                      setIsPaused(false)
                    } else {
                      handle(() => pauseAutomation(sessionId), 'pause')
                      setIsPaused(true)
                    }
                  }}
                >
                  {isPaused ? <Play size={14} /> : <Pause size={14} />}
                  {isPaused ? 'Resume' : 'Pause'}
                </button>
                <button
                  className="bg-red-900 hover:bg-red-800 text-red-200 flex-1 flex items-center justify-center gap-1.5 text-sm rounded-lg px-3 py-2 transition-colors"
                  onClick={() => { handle(() => stopAutomation(sessionId), 'stop'); onClose() }}
                >
                  <Square size={14} />
                  Stop
                </button>
              </div>
            </div>

            {/* Event log */}
            <div className="flex-1 overflow-y-auto p-3">
              <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-2">
                Event Log ({events.length})
              </p>
              <div className="space-y-1.5">
                {events.length === 0 && (
                  <p className="text-xs text-gray-600 italic">No events yet…</p>
                )}
                {[...events].reverse().map((evt, i) => (
                  <div
                    key={i}
                    className={`text-xs rounded-lg p-2 ${
                      evt.status === 'error' ? 'bg-red-950 text-red-300' :
                      evt.status === 'paused' ? 'bg-yellow-950 text-yellow-300' :
                      'bg-gray-800 text-gray-300'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-1 mb-0.5">
                      <span className="font-mono text-[10px] text-gray-500">{evt.step}</span>
                      {evt.timestamp && (
                        <span className="text-[10px] text-gray-600">
                          {formatDistanceToNow(new Date(evt.timestamp), { addSuffix: true })}
                        </span>
                      )}
                    </div>
                    <p>{evt.message}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
