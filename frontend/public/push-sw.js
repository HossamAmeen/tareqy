// Imported by the generated service worker (see vite.config.ts). Payloads carry no personal data.
self.addEventListener('push', (event) => {
  let data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch {
    /* fall back to a generic message */
  }
  event.waitUntil(
    self.registration.showNotification(data.title || 'في طريقي', {
      body: data.body || 'لديك إشعار جديد',
      icon: '/pwa-192x192.png',
      tag: data.notification_id ? `n-${data.notification_id}` : undefined,
      lang: 'ar',
      dir: 'rtl',
      data: { url: '/notifications' },
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = (event.notification.data && event.notification.data.url) || '/'
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if ('focus' in client) {
          client.navigate(url)
          return client.focus()
        }
      }
      return self.clients.openWindow(url)
    }),
  )
})
