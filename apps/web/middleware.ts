import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString('base64')

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // Create CSP
  // - default-src 'self'
  // - script-src 'self' 'nonce-...' 'strict-dynamic' (allows Next.js chunks)
  // - style-src 'self' 'unsafe-inline' (Next.js and Tiptap often require inline styles)
  // - img-src 'self' data: (allow data URIs for images if needed)
  // - connect-src 'self' and apiUrl
  const isDev = process.env.NODE_ENV !== 'production'
  const isCI = process.env.CI === 'true'
  const includeUpgradeInsecure = !isDev && !isCI
  const cspHeader = `
    default-src 'self';
    script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${isDev ? " 'unsafe-eval'" : ""};
    style-src 'self' 'unsafe-inline';
    img-src 'self' blob: data:;
    font-src 'self';
    object-src 'none';
    base-uri 'self';
    form-action 'self';
    frame-ancestors 'none';
    block-all-mixed-content;
    ${includeUpgradeInsecure ? "upgrade-insecure-requests;" : ""}
    connect-src 'self' ${apiUrl};
  `.replace(/\s{2,}/g, ' ').trim()

  const requestHeaders = new Headers(request.headers)
  requestHeaders.set('x-nonce', nonce)
  requestHeaders.set('Content-Security-Policy', cspHeader)

  const response = NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  })

  response.headers.set('Content-Security-Policy', cspHeader)
  return response
}

export const config = {
  matcher: [
    {
      source: '/((?!api|_next/static|_next/image|favicon.ico).*)',
      missing: [
        { type: 'header', key: 'next-router-prefetch' },
        { type: 'header', key: 'purpose', value: 'prefetch' },
      ],
    },
  ],
}
