const V="lacesta-v8";
const CORE=["./","index.html","config.js","manifest.webmanifest","icons/icon.svg","icons/icon-192.png","icons/icon-512.png"];
self.addEventListener("install",e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting()));});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener("fetch",e=>{
  const r=e.request;if(r.method!=="GET")return;
  const u=new URL(r.url);
  // precios.json: red primero, para que los precios nuevos lleguen; si no hay red, la copia guardada
  if(u.origin===location.origin&&u.pathname.endsWith("/precios.json")){
    e.respondWith(fetch(r).then(res=>{const cp=res.clone();caches.open(V).then(c=>c.put(r,cp));return res;}).catch(()=>caches.match(r)));return;
  }
  // resto de la app y tipografías: copia guardada primero y se refresca en segundo plano
  if(u.origin===location.origin||u.host==="fonts.googleapis.com"||u.host==="fonts.gstatic.com"){
    e.respondWith(caches.match(r).then(hit=>{
      const net=fetch(r).then(res=>{if(res&&(res.ok||res.type==="opaque")){const cp=res.clone();caches.open(V).then(c=>c.put(r,cp));}return res;}).catch(()=>hit);
      return hit||net;
    }));
  }
});
