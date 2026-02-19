const CACHE_NAME = 'santer-saude-v2'; // Mude a versão sempre que atualizar o app
const ASSETS_TO_CACHE = [
    '/entrar',
    '/static/manifest.json',
    '/static/icon-192.png'
];

// Instalação: Salva arquivos básicos no cache
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
    self.skipWaiting();
});

// Ativação: Limpa caches de versões anteriores
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
            );
        })
    );
});

// Estratégia de busca (Fetch)
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // 1. IGNORAR ROTAS DE AUTH E ADMIN (Sempre buscar na internet)
    if (url.pathname.includes('/auth/') || url.pathname.includes('/logout') || url.pathname.includes('/admin')) {
        return; 
    }

    // 2. ESTRATÉGIA: Tenta a internet, se falhar, tenta o cache
    event.respondWith(
        fetch(event.request).catch(() => {
            return caches.match(event.request);
        })
    );
});
