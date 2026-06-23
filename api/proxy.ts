import { VercelRequest, VercelResponse } from '@vercel/node'

// The backend is a bare IP behind nginx that redirects HTTP -> HTTPS and serves
// a self-signed certificate (no valid CA cert is possible without a domain).
// Node's built-in fetch (undici) rejects self-signed certs with
// DEPTH_ZERO_SELF_SIGNED_CERT, and it ignores the `agent` option, so we disable
// TLS verification process-wide for this proxy function. This is the documented
// way to make the native fetch accept self-signed certs.
//
// SECURITY TRADEOFF: this disables MITM protection on the proxy -> backend hop.
// Acceptable only for a single-user, bare-IP backend. Long-term fix: give the
// backend a real domain + Let's Encrypt cert and remove this line.
process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0'

// Statically-named proxy function. All /api/* requests are rewritten to
// /api/proxy?path=<segments> by vercel.json, so this does NOT depend on
// dynamic catch-all route registration (which proved unreliable for
// multi-segment paths in this project's Vite + outputDirectory setup).
//
// Fallback targets port 80 (nginx); port 8000 is blocked by the EC2 security
// group. In production, BACKEND_API_URL should be set in the Vercel dashboard.
const BACKEND_URL = (process.env.BACKEND_API_URL || 'http://54.237.223.146').replace(/\/+$/, '')

export default async (req: VercelRequest, res: VercelResponse) => {
  // The original path after /api is delivered via the rewrite's `path` param.
  const rawPath = req.query.path
  const pathStr = Array.isArray(rawPath) ? rawPath.join('/') : (rawPath || '')
  const path = pathStr ? `/${pathStr.replace(/^\/+/, '')}` : ''

  // Forward every query param except the internal `path` capture.
  const { path: _omit, ...restQuery } = req.query
  const flatQuery: Record<string, string> = {}
  for (const [k, v] of Object.entries(restQuery)) {
    flatQuery[k] = Array.isArray(v) ? v.join(',') : (v as string)
  }
  const queryString = new URLSearchParams(flatQuery).toString()

  const fullUrl = `${BACKEND_URL}/api${path}${queryString ? `?${queryString}` : ''}`

  // CORS headers (set early so they apply to error responses too).
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

    // File uploads (FormData): pass through the raw body and let fetch handle content-type.
    if ((req.headers['content-type'] as string)?.includes('multipart/form-data')) {
      // Don't set Content-Type header — let fetch/Node infer it from body
      fetchOptions.body = req.body
    } else if (reqMethod !== 'GET' && reqMethod !== 'HEAD' && req.body) {
      headers['Content-Type'] = 'application/json'
      fetchOptions.body = JSON.stringify(req.body)
    } else {
      // No body — set JSON content-type as default
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
