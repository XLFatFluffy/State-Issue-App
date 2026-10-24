/* State Issue 3.1.0 offline application shell.
   The worker is registered only by the host computer's localhost tab.
   API responses are never cached. HTML is cached only after stripping the
   server-injected state so personal records are not copied into the shell cache. */
'use strict';
const CACHE_NAME = 'state-issue-shell-v3.1.0';
const SHELL_URLS = ['/', '/Stateissue.html'];
function shellOnly(response) {
  // Cache only the app shell, never the server-injected copy of operational data.
  return response.text().then(text => {
    const safeText = text.replace(/<script>window\.__STATE_ISSUE_SERVER_STATE__=[\s\S]*?;<\/script>/, '');
    return new Response(safeText, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers
    });
  });
}
self.addEventListener('install', event => {
  // Pre-cache both entry URLs so navigation still works during a host outage.
  event.waitUntil(caches.open(CACHE_NAME).then(cache => Promise.all(SHELL_URLS.map(url =>
    fetch(url).then(response => {
      if (!response.ok) throw new Error('Unable to cache State Issue shell: ' + url);
      return shellOnly(response.clone()).then(safeResponse => cache.put(url, safeResponse));
    })
  ))).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  // Remove old versioned shells after the new worker takes control.
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(key => key.startsWith('state-issue-shell-') && key !== CACHE_NAME).map(key => caches.delete(key))
  )).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;
  if (request.mode === 'navigate' || SHELL_URLS.includes(url.pathname)) {
    // Prefer the live server; use the sanitized shell only when it is unreachable.
    event.respondWith(fetch(request).then(response => {
      if (response && response.ok) {
        shellOnly(response.clone()).then(safeResponse => caches.open(CACHE_NAME).then(cache => cache.put(url.pathname, safeResponse))).catch(() => {});
      }
      return response;
    }).catch(() => caches.match(url.pathname).then(cached => cached || caches.match('/')).then(cached => cached || new Response(
      'State Issue has not finished loading on this computer yet. ' +
      'Open it once while the server is running, then it will also work offline.',
      { status: 503, headers: { 'Content-Type': 'text/plain' } }
    ))));
  }
});
