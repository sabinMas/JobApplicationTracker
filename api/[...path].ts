import { VercelRequest, VercelResponse } from '@vercel/node'

// Disable TLS verification for self-signed certs on backend
process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0'

const BACKEND_URL = (process.env.BACKEND_API_URL || 'http://54.237.223.146').replace(/\/+$/, '')

export default async (req: VercelRequest, res: VercelResponse) => {
  // Extract the path from the catch-all parameter
  const pathSegments = req.query.path as string[]
  const path = pathSegments ? `/${pathSegments.join('/')}` : ''

  // Build query string from remaining query params
  const flatQuery: Record<string, string> = {}
  for (const [k, v] of Object.entries(req.query)) {
    if (k !== 'path') {
      flatQuery[k] = Array.isArray(v) ? v.join(',') : (v as string)
    }
  }
  const queryString = new URLSearchParams(flatQuery).toString()

  const fullUrl = `${BACKEND_URL}/api${path}${queryString ? `?${queryString}` : ''}`

  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, PATCH, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization')

  const reqMethod = req.method || 'GET'
  if (reqMethod === 'OPTIONS') {
    return res.status(204).end()
  }

  try {
    const headers: Record<string, string> = {}
    if (req.headers.authorization) {
      headers['Authorization'] = req.headers.authorization as string
    }

    const fetchOptions: Record<string, any> = { method: reqMethod, headers }

    // Handle multipart form-data
    if ((req.headers['content-type'] as string)?.includes('multipart/form-data')) {
      fetchOptions.body = req.body
    } else if (reqMethod !== 'GET' && reqMethod !== 'HEAD' && req.body) {
      headers['Content-Type'] = 'application/json'
      fetchOptions.body = JSON.stringify(req.body)
    } else {
      headers['Content-Type'] = 'application/json'
    }

    const response = await fetch(fullUrl, fetchOptions as RequestInit)
    const contentType = response.headers.get('content-type')

    if (contentType?.includes('application/json')) {
      const data = await response.json()
      return res.status(response.status).json(data)
    }

    const buffer = await response.arrayBuffer()
    if (contentType) res.setHeader('Content-Type', contentType)
    return res.status(response.status).send(Buffer.from(buffer))
  } catch (error) {
    const err = error as Error & { cause?: { code?: string; message?: string } }
    const cause = err.cause
    console.error(`Proxy error for ${reqMethod} ${fullUrl}:`, err, cause)
    return res.status(502).json({
      detail: `Backend unavailable: ${err.message}`,
      cause: cause ? `${cause.code || ''} ${cause.message || cause}`.trim() : undefined,
      target: fullUrl,
    })
  }
}
