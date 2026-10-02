import fs from 'fs';
import path from 'path';

export async function GET() {
  let filePath = path.join(process.cwd(), 'public', 'index.html');
  if (!fs.existsSync(filePath)) {
    filePath = path.join(process.cwd(), 'frontend', 'public', 'index.html');
  }

  try {
    let html = fs.readFileSync(filePath, 'utf8');

    // If NEXT_PUBLIC_API_URL is configured, inject it into the page window
    const rawApiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (rawApiUrl) {
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
