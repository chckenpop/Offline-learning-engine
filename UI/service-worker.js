const CACHE_NAME = 'offline-learning-v5';

// Add all the files we want to cache right away when the app is installed
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/styles.css',
    '/main.js',
    '/manifest.json'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('Opened cache');
            return cache.addAll(STATIC_ASSETS);
        })
    );
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    const cleanPath = url.pathname;

    // 1. Skip non-GET requests
    if (event.request.method !== 'GET') return;

    // 2. Special handling for API calls (Network-First, then Cache)
    if (cleanPath.startsWith('/api/')) {
        event.respondWith(
            fetch(event.request)
                .then((networkResponse) => {
                    const clonedResponse = networkResponse.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, clonedResponse);
                    });
                    return networkResponse;
                })
                .catch(() => {
                    return caches.match(event.request);
                })
        );
        return;
    }

    // 3. Static Assets (Bust query strings for caching)
    // We match by pathname only so styles.css?v=123 matches /styles.css in cache
    event.respondWith(
        caches.match(cleanPath).then((cachedResponse) => {
            if (cachedResponse) {
                return cachedResponse;
            }
            return fetch(event.request).then((networkResponse) => {
                // If it's a static file, cache it under the cleanPath for future offline use
                if (networkResponse.ok && (
                    cleanPath.match(/\.(js|css|png|jpg|jpeg|svg|ico|json)$/) ||
                    cleanPath === '/' ||
                    cleanPath === '/index.html'
                )) {
                    const clonedResponse = networkResponse.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(cleanPath, clonedResponse);
                    });
                }
                return networkResponse;
            });
        })
    );
});

self.addEventListener('activate', (event) => {
    // Cleanup old caches
    const cacheWhitelist = [CACHE_NAME];
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheWhitelist.indexOf(cacheName) === -1) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});
