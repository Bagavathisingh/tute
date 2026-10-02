import fs from 'fs';
import path from 'path';

export async function GET() {
  let filePath = path.join(process.cwd(), 'public', 'index.html');
  if (!fs.existsSync(filePath)) {
    filePath = path.join(process.cwd(), 'frontend', 'public', 'index.html');
  }

  try {
    let html = fs.readFileSync(filePath, 'utf8');

    // Only inject API_BASE for local development (localhost URLs).
    // For production, let app.js use relative "/api" so Next.js rewrites proxy
    // the request server-side, avoiding CORS issues entirely.
    const rawApiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (rawApiUrl && rawApiUrl.includes('localhost')) {
      const cleanUrl = rawApiUrl.replace(/\/$/, '');
      const apiBase = cleanUrl.endsWith('/api') ? cleanUrl : `${cleanUrl}/api`;
      html = html.replace('<head>', `<head><script>window.API_BASE = "${apiBase}";</script>`);
    }

    return new Response(html, {
      headers: {
        'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'no-store, no-cache, must-revalidate',
      },
    });
  } catch (err) {
    console.error('[Route Handler] Could not serve index.html:', err);
    return new Response('Application template not found. Please verify deployment build assets.', {
      status: 500,
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
      },
    });
  }
}
