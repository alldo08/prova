// sw.js - Service Worker Básico
self.addEventListener('install', (event) => {
    console.log('Service Worker instalado!');
});

self.addEventListener('fetch', (event) => {
    // Esse código permite que o app funcione até com internet ruim
    event.respondWith(fetch(event.request));
});
