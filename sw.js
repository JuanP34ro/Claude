/* Carp Field Notes: service worker.
 * 1) App sin conexión: guarda solo la propia app (HTML, manifiesto e iconos), red primero (4 s).
 * 2) Mapas sin conexión: sirve las imágenes que el usuario descargó a propósito en «Mapas sin conexión»
 *    (caché cfn-tiles-*). Nunca guarda por su cuenta mapas, /api/ ni el tiempo. */
const CACHE='cfn-shell-v1',TILES='cfn-tiles-v1';
const SHELL=['./','./index.html','./manifest.webmanifest','./icon.svg','./apple-touch-icon.png','./icon-192.png','./icon-512.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE&&!k.startsWith('cfn-tiles')).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
// Misma clave que tileKey() en app.js: capa + extensión + formato, sin importar si la petición va al IGN o al proxy.
function tileKey(url){const p={};for(const[k,v]of url.searchParams)p[k.toUpperCase()]=v;if((p.REQUEST||'').toLowerCase()!=='getmap'||!p.LAYERS||!p.BBOX)return null;return `https://cfn.offline/tile?l=${encodeURIComponent(p.LAYERS)}&b=${p.BBOX}&f=${encodeURIComponent(p.FORMAT||'')}`;}
self.addEventListener('fetch',e=>{
  const req=e.request;if(req.method!=='GET')return;
  const url=new URL(req.url),key=tileKey(url);
  if(key){e.respondWith((async()=>{try{if(await caches.has(TILES)){const hit=await (await caches.open(TILES)).match(key);if(hit)return hit;}}catch{}return fetch(req);})());return;}
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
      return res;
    }catch{
      return (await cache.match(shellKey,{ignoreSearch:true}))||(await cache.match(new URL('./',self.registration.scope).href))||Response.error();
    }
  })());
});
