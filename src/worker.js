const USER_AGENTS = {
  'chrome-desktop': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
  'chrome-mobile': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36',
  'googlebot': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
  'outlook-2019': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; Trident/7.0; rv:11.0) like Gecko',
  'apple-mail': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko)'
};

export default {
  async fetch(request, env, ctx) {
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type'
        }
      });
    }

    if (request.method !== 'POST') {
      return new Response(JSON.stringify({ success: false, error: 'POST required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
      });
    }

    try {
      const { url, userAgent } = await request.json();

      if (!url) {
        return jsonResponse({ success: false, error: 'url parameter required' }, 400);
      }

      let urlObj;
      try {
        urlObj = new URL(url);
      } catch {
        return jsonResponse({ success: false, error: 'Invalid URL format' }, 400);
      }

      if (!['http:', 'https:'].includes(urlObj.protocol)) {
        return jsonResponse({ success: false, error: 'Only http:// and https:// supported' }, 400);
      }

      const ua = USER_AGENTS[userAgent] || USER_AGENTS['chrome-desktop'];
      const startTime = Date.now();
      const chain = await followRedirects(url, ua, 15);
      const elapsedMs = Date.now() - startTime;

      return jsonResponse({
        success: true,
        chain: chain,
        elapsed_ms: elapsedMs
      });
    } catch (error) {
      const message = error.message || 'Unknown error';
      return jsonResponse({
        success: false,
        error: mapErrorMessage(message)
      }, 500);
    }
  }
};

async function followRedirects(url, userAgent, maxHops) {
  const chain = [];
  let currentUrl = url;
  let hopCount = 0;
  const visited = new Set();

  while (hopCount < maxHops) {
    if (visited.has(currentUrl)) {
      break; // Avoid infinite redirect loops
    }
    visited.add(currentUrl);

    try {
      const response = await fetch(currentUrl, {
        method: 'HEAD',
        headers: { 'User-Agent': userAgent },
        redirect: 'manual',
        timeout: 15000
      });

      const status = response.status;
      chain.push({
        status: status,
        url: currentUrl
      });

      if ([301, 302, 303, 307, 308].includes(status)) {
        const location = response.headers.get('Location');
        if (!location) break; // No Location header, treat as final
        currentUrl = new URL(location, currentUrl).toString();
        hopCount++;
      } else {
        break;
      }
    } catch (error) {
      chain.push({
        status: 'Error',
        url: currentUrl,
        error: mapErrorMessage(error.message)
      });
      break;
    }
  }

  return chain;
}

function mapErrorMessage(err) {
  const msg = err.toLowerCase();
  if (msg.includes('timeout')) return 'Request timed out after 15s';
  if (msg.includes('dns')) return 'Could not resolve hostname';
  if (msg.includes('econnrefused')) return 'Connection failed — host may be offline';
  if (msg.includes('enotfound')) return 'Could not resolve hostname';
  return 'Request failed — try again in a moment';
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*'
    }
  });
}
