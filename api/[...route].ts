import { VercelRequest, VercelResponse } from '@vercel/node'
import https from 'https'

const BACKEND_URL = process.env.BACKEND_API_URL || 'http://54.237.223.146:8000'

// Allow self-signed certificates (for nginx reverse proxy with self-signed SSL)
const httpsAgent = new https.Agent({ rejectUnauthorized: false })

export default async (req: VercelRequest, res: VercelResponse) => {
  const { route, ...restQuery } = req.query
  const pathSegments = Array.isArray(route) ? route : [route]
  const path = `/${pathSegments.join('/')}`

  try {
    const reqMethod = req.method || 'GET'
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    // Forward authentication headers if present
    if (req.headers.authorization) {
      headers['Authorization'] = req.headers.authorization as string
    }

    const fetchOptions: Record<string, any> = {
      method: reqMethod,
      headers,
    }

    // Forward body for POST/PUT/PATCH requests
    if (reqMethod !== 'GET' && reqMethod !== 'HEAD' && req.body) {
      fetchOptions.body = JSON.stringify(req.body)
    }

    // Handle file uploads (FormData)
    if ((req.headers['content-type'] as string)?.includes('multipart/form-data')) {
      delete headers['Content-Type'] // Let fetch set it with boundary
      fetchOptions.body = req.body
    }

    // Build query string — exclude the internal 'route' catch-all param
    const queryString = new URLSearchParams(restQuery as Record<string, string>)
      .toString()
    const fullUrl = `${BACKEND_URL}/api${path}${queryString ? `?${queryString}` : ''}`

    const response = await fetch(fullUrl, {
      ...fetchOptions,
      agent: fullUrl.startsWith('https') ? httpsAgent : undefined,
    } as RequestInit)
    const contentType = response.headers.get('content-type')

    // Set CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*')
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, PATCH, OPTIONS')
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    if (contentType?.includes('application/json')) {
      const data = await response.json()
      return res.status(response.status).json(data)
    }

    // For non-JSON responses (PDFs, etc.)
    const buffer = await response.arrayBuffer()
    if (contentType) {
      res.setHeader('Content-Type', contentType)
    }
    return res.status(response.status).send(Buffer.from(buffer))
  } catch (error) {
    console.error(`Proxy error for ${req.method} ${path}:`, error)
    return res.status(502).json({
      detail: `Backend unavailable: ${(error as Error).message}`,
    })
  }
}
