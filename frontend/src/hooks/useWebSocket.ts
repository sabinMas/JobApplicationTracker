import { useEffect, useRef, useState, useCallback } from 'react'

export interface WSEvent {
  session_id: string
  step: string
  status: 'running' | 'paused' | 'done' | 'error'
  message: string
  screenshot_b64?: string
  timestamp?: string
}

export function useAutomationWebSocket(sessionId: string | null) {
  const [events, setEvents] = useState<WSEvent[]>([])
  const [latestScreenshot, setLatestScreenshot] = useState<string | null>(null)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!sessionId) return

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${protocol}://${window.location.host}/api/automation/ws/${sessionId}`)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping')
      }, 15000)
    }

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as WSEvent & { type?: string }
        if (data.type === 'pong') return
        setEvents(prev => [...prev.slice(-99), data])  // keep last 100 events
        if (data.screenshot_b64) {
          setLatestScreenshot(data.screenshot_b64)
        }
      } catch { /* ignore malformed messages */ }
    }

    ws.onclose = () => {
      setConnected(false)
      if (pingRef.current) clearInterval(pingRef.current)
    }

    return () => {
      ws.close()
      if (pingRef.current) clearInterval(pingRef.current)
    }
  }, [sessionId])

  const clearEvents = useCallback(() => setEvents([]), [])

  return { events, latestScreenshot, connected, clearEvents }
}
