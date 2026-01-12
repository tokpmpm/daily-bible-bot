/* ============================================
   每日靈修 - Service Worker
   ============================================ */

const CACHE_NAME = 'daily-bible-v2';

// Install event - skip waiting immediately
self.addEventListener('install', (event) => {
    console.log('SW installing...');
    self.skipWaiting();
});

// Activate event - take control immediately
self.addEventListener('activate', (event) => {
    console.log('SW activating...');
    event.waitUntil(
        Promise.all([
            // Clean up old caches
            caches.keys().then((cacheNames) => {
                return Promise.all(
                    cacheNames.filter(name => name !== CACHE_NAME)
                        .map(name => caches.delete(name))
                );
            }),
            // Take control of all clients
            self.clients.claim()
        ])
    );
});

// Fetch event - network first, cache fallback
self.addEventListener('fetch', (event) => {
    event.respondWith(
        fetch(event.request)
            .catch(() => caches.match(event.request))
    );
});

// Push event - show notification
self.addEventListener('push', (event) => {
    let data = {
        title: '📖 每日靈修',
        body: '今天的靈修已經準備好了！',
        url: '/'
    };

    try {
        if (event.data) {
            data = event.data.json();
        }
    } catch (e) {
        console.error('Error parsing push data:', e);
    }

    const options = {
        body: data.body,
        icon: '/icon-192.png',
        vibrate: [100, 50, 100],
        data: {
            url: data.url || '/'
        },
        actions: [
            {
                action: 'open',
                title: '立即查看'
            }
        ]
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Notification click event - open the app
self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    const urlToOpen = event.notification.data?.url || '/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                for (const client of clientList) {
                    if (client.url.includes(self.location.origin) && 'focus' in client) {
                        return client.focus();
                    }
                }
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});
