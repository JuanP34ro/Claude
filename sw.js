/* Carp Field Notes: service worker.
 * Guarda solo la propia app (HTML, manifiesto e iconos), red primero (4 s), para abrirla sin cobertura.
 * No toca las imágenes de mapa: las guardadas en «Mapas sin conexión» (caché cfn-tiles-*) las lee la propia app,
 * y las demás van directas a Internet. Nunca guarda por su cuenta mapas, /api/ ni el tiempo. */
const CACHE='cfn-shell-v2';
const SHELL=['./','./index.html','./manifest.webmanifest','./icon.svg','./apple-touch-icon.png','./icon-192.png','./icon-512.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE&&!k.startsWith('cfn-tiles')).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
  const req=e.request;if(req.method!=='GET')return;
  const url=new URL(req.url);
  if(url.origin!==self.location.origin||url.pathname.includes('/api/'))return;
  const scope=new URL(self.registration.scope).pathname,isPage=req.mode==='navigate';
  if(!isPage&&!SHELL.some(p=>new URL(p,self.registration.scope).pathname===url.pathname))return;
  const shellKey=isPage?new URL('./index.html',self.registration.scope).href:req;
  e.respondWith((async()=>{
    const cache=await caches.open(CACHE);
    try{
      const ctrl=new AbortController(),t=setTimeout(()=>ctrl.abort(),4000);
      const res=await fetch(req,{signal:ctrl.signal,cache:'no-cache'});clearTimeout(t);
      if(res.ok&&url.pathname.startsWith(scope))await cache.put(shellKey,res.clone());
      // Alojamiento caído o pausado (error 4xx/5xx): se abre la copia guardada de la app en vez de la página de error.
      if(!res.ok&&isPage){const hit=await cache.match(shellKey,{ignoreSearch:true});if(hit)return hit;}
      return res;
    }catch{
      return (await cache.match(shellKey,{ignoreSearch:true}))||(await cache.match(new URL('./',self.registration.scope).href))||Response.error();
    }
  })());
});
