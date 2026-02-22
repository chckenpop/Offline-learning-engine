const CACHE_NAME = 'offline-learning-v4';

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
    // Only intercept GET requests, skip API calls for now because the backend handles them
    if (event.request.method !== 'GET') return;

    // Pass strictly API requests through to the network
    if (event.request.url.includes('/api/')) {
        return;
    }

    // Cache-First strategy for static files (HTML, CSS, JS, Images)
    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {
            if (cachedResponse) {
                return cachedResponse; // Return from cache
            }
            // Fetch from network if not in cache
            return fetch(event.request).then((networkResponse) => {
                // Return network response right away, and optionally add to cache later if needed
                return networkResponse;
            });
        }).catch(() => {
            // If the network fails and we don't have it in cache, we could return a fallback HTML here
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
