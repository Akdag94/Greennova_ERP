/**
 * GreenNova ERP — Service Worker
 * Strateji:
 *   - Statik dosyalar (CSS, JS, fontlar): Cache First
 *   - API istekleri: Network First, offline'da hata dönülür
 *   - QR sayfası: Cache First (offline çalışsın)
 *   - Background Sync: offline kuyruğu otomatik göndermek için
 */

const CACHE_NAME = 'greennova-v1';
const OFFLINE_CACHE = 'greennova-offline-v1';

// Çevrimdışıyken önbellekte tutulacak sayfalar
const PRECACHE_URLS = [
    '/inventory/scan/',
    '/inventory/mobil-giris/',
    '/static/manifest.json',
    // html5-qrcode CDN — Service Worker CDN'i cachleyemez,
    // ama fetch handler'da yönetebiliriz
];

// ============================================================
// INSTALL: kritik dosyaları önceden önbellekle
// ============================================================
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(OFFLINE_CACHE).then((cache) => {
            return cache.addAll(PRECACHE_URLS).catch(err => {
                console.warn('[SW] Precache hatası (bazı kaynaklar yüklenemedi):', err);
            });
        })
    );
    self.skipWaiting();
});

// ============================================================
// ACTIVATE: eski cache'leri temizle
// ============================================================
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter(key => key !== CACHE_NAME && key !== OFFLINE_CACHE)
                    .map(key => caches.delete(key))
            )
        )
    );
    self.clients.claim();
});

// ============================================================
// FETCH: istek yakalama stratejisi
// ============================================================
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // 1) API istekleri → Network First (offline'da kuyruğa alınacak)
    if (url.pathname.startsWith('/inventory/api/') ||
        url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirst(event.request));
        return;
    }

    // 2) Admin sayfaları → Network Only (cache'leme)
    if (url.pathname.startsWith('/admin/')) {
        event.respondWith(fetch(event.request).catch(() =>
            new Response('Admin offline kullanılamaz.', {
                status: 503,
                headers: { 'Content-Type': 'text/plain; charset=utf-8' }
            })
        ));
        return;
    }

    // 3) Statik dosyalar → Cache First
    if (url.pathname.startsWith('/static/') ||
        url.pathname.startsWith('/media/') ||
        event.request.destination === 'script' ||
        event.request.destination === 'style' ||
        event.request.destination === 'font') {
        event.respondWith(cacheFirst(event.request));
        return;
    }

    // 4) Sayfalar (QR terminali, mobil giris) → Stale While Revalidate
    event.respondWith(staleWhileRevalidate(event.request));
});

// ============================================================
// Strateji: Network First
// ============================================================
async function networkFirst(request) {
    try {
        const response = await fetch(request);
        // Başarılı API yanıtlarını cache'e al (GET için)
        if (request.method === 'GET' && response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }
        return response;
    } catch (err) {
        // Network yok → cache'e bak
        const cached = await caches.match(request);
        if (cached) return cached;
        // Cache'de de yok → offline JSON hatası
        return new Response(
            JSON.stringify({ status: 'error', message: 'Çevrimdışısınız. İşlem kuyruğa alındı.' }),
            {
                status: 503,
                headers: { 'Content-Type': 'application/json; charset=utf-8' }
            }
        );
    }
}

// ============================================================
// Strateji: Cache First
// ============================================================
async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) return cached;
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }
        return response;
    } catch (err) {
        return new Response('Kaynak bulunamadı ve offline.', { status: 503 });
    }
}

// ============================================================
// Strateji: Stale While Revalidate
// ============================================================
async function staleWhileRevalidate(request) {
    const cache = await caches.open(OFFLINE_CACHE);
    const cached = await cache.match(request);

    const fetchPromise = fetch(request).then(response => {
        if (response.ok) cache.put(request, response.clone());
        return response;
    }).catch(() => null);

    return cached || fetchPromise || new Response(
        offlinePageHtml(),
        { headers: { 'Content-Type': 'text/html; charset=utf-8' } }
    );
}

// ============================================================
// Offline sayfası
// ============================================================
function offlinePageHtml() {
    return `<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Çevrimdışı — GreenNova</title>
    <style>
        body { background: #121212; color: #e0e0e0; font-family: sans-serif;
               display: flex; align-items: center; justify-content: center;
               min-height: 100vh; margin: 0; text-align: center; }
        h1 { color: #28a745; }
        p { color: #888; }
        a { color: #28a745; }
    </style>
</head>
<body>
    <div>
        <h1>📵 Çevrimdışısınız</h1>
        <p>İnternet bağlantısı yok. QR terminali offline çalışmaya devam eder.</p>
        <p><a href="/inventory/scan/">QR Terminaline Git →</a></p>
    </div>
</body>
</html>`;
}

// ============================================================
// Background Sync (Chrome destekli)
// Offline kuyruktaki işlemleri bağlantı gelince otomatik gönder
// ============================================================
self.addEventListener('sync', (event) => {
    if (event.tag === 'greennova-sync') {
        event.waitUntil(backgroundSync());
    }
});

async function backgroundSync() {
    // IndexedDB'ye erişim için istemciye mesaj at
    // (Service Worker'da IndexedDB erişimi sınırlı)
    const clients = await self.clients.matchAll();
    for (const client of clients) {
        client.postMessage({ type: 'TRIGGER_SYNC' });
    }
}

// ============================================================
// Push Notification (ileride kullanım için hazır)
// ============================================================
self.addEventListener('push', (event) => {
    if (!event.data) return;
    const data = event.data.json();
    event.waitUntil(
        self.registration.showNotification(data.title || 'GreenNova', {
            body: data.body || '',
            icon: '/static/icons/icon-192.png',
            badge: '/static/icons/icon-192.png',
            tag: 'greennova-push',
            data: { url: data.url || '/inventory/scan/' }
        })
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const url = event.notification.data?.url || '/inventory/scan/';
    event.waitUntil(clients.openWindow(url));
});
