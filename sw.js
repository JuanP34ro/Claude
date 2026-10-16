/* Carp Field Notes: service worker.
 * Guarda solo la propia app (HTML, manifiesto e iconos), red primero, para abrirla sin cobertura. Si la red tarda más de 4 s se abre la
 * copia guardada y la descarga sigue de fondo, para que la próxima apertura ya tenga la versión nueva.
 * No toca las imágenes de mapa: las guardadas en «Mapas sin conexión» (caché cfn-tiles-*) las lee la propia app,
 * y las demás van directas a Internet. Nunca guarda por su cuenta mapas, /api/ ni el tiempo. */
const CACHE='cfn-shell-v2',VERSION='4';
const SHELL=['./','./index.html','./manifest.webmanifest','./icon.svg','./apple-touch-icon.png','./icon-192.png','./icon-512.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE&&!k.startsWith('cfn-tiles')).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
// La app pregunta la versión para el diagnóstico (un worker antiguo no contesta).
self.addEventListener('message',e=>{if(e.data==='version'&&e.ports?.[0])e.ports[0].postMessage(VERSION);});
self.addEventListener('fetch',e=>{
  const req=e.request;if(req.method!=='GET')return;
  const url=new URL(req.url);
  if(url.origin!==self.location.origin||url.pathname.includes('/api/'))return;
  const scope=new URL(self.registration.scope).pathname,isPage=req.mode==='navigate';
  if(!isPage&&!SHELL.some(p=>new URL(p,self.registration.scope).pathname===url.pathname))return;
  const shellKey=isPage?new URL('./index.html',self.registration.scope).href:req;
  e.respondWith((async()=>{
    const cache=await caches.open(CACHE);
    const cached=async()=>(await cache.match(shellKey,{ignoreSearch:true}))||(isPage?await cache.match(new URL('./',self.registration.scope).href):undefined);
    // Sin abortar la red: con cobertura floja, cortar la descarga a los 4 s dejaba la versión antigua en el móvil para siempre.
    const net=fetch(req,{cache:'no-cache'}).then(async res=>{if(res.ok&&url.pathname.startsWith(scope))await cache.put(shellKey,res.clone());return res;}).catch(()=>null);
    const first=await Promise.race([net,new Promise(r=>setTimeout(()=>r('slow'),4000))]);
    if(first&&first!=='slow'){
      // Alojamiento caído o pausado (error 4xx/5xx): se abre la copia guardada de la app en vez de la página de error.
      if(!first.ok&&isPage){const hit=await cached();if(hit)return hit;}
      return first;
    }
    const hit=await cached();
    if(hit){e.waitUntil(net);return hit;}
    return (await net)||Response.error();
  })());
});
