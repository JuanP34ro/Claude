/* Carp Field Notes: service worker mínimo para que la app abra sin cobertura.
 * Solo guarda la propia app (HTML, manifiesto e iconos). Nunca guarda mapas, /api/ ni el tiempo.
 * Red primero (4 s) para recibir siempre la última versión; si no hay red, la copia guardada. */
const CACHE='cfn-shell-v1';
const SHELL=['./','./index.html','./manifest.webmanifest','./icon.svg','./apple-touch-icon.png','./icon-192.png','./icon-512.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
  const req=e.request;if(req.method!=='GET')return;
  const url=new URL(req.url);if(url.origin!==self.location.origin||url.pathname.includes('/api/'))return;
  const scope=new URL(self.registration.scope).pathname;
  const isPage=req.mode==='navigate';
  if(!isPage&&!SHELL.some(p=>new URL(p,self.registration.scope).pathname===url.pathname))return;
  const key=isPage?new URL('./index.html',self.registration.scope).href:req;
  e.respondWith((async()=>{
    const cache=await caches.open(CACHE);
    try{
      const ctrl=new AbortController(),t=setTimeout(()=>ctrl.abort(),4000);
      const res=await fetch(req,{signal:ctrl.signal,cache:'no-cache'});clearTimeout(t);
      if(res.ok&&url.pathname.startsWith(scope))await cache.put(key,res.clone());
      return res;
    }catch{
      return (await cache.match(key,{ignoreSearch:true}))||(await cache.match(new URL('./',self.registration.scope).href))||Response.error();
    }
  })());
});
