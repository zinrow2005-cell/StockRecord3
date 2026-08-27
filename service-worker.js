const CACHE_VERSION = "安心股票簿-github-pwa-2026-08-27-18";
const SHELL_CACHE = `${CACHE_VERSION}-shell`;
const ASSET_CACHE = `${CACHE_VERSION}-assets`;
const BASE_URL = new URL("./", self.location.href);
const appPath = (name = "") => new URL(name, BASE_URL).pathname;
const APP_URL = appPath();
const OFFLINE_URL = appPath("offline.html");
const CORE_FILES = [
  OFFLINE_URL,
  appPath("manifest.webmanifest"),
  appPath("favicon.svg"),
  appPath("icon-192.png"),
  appPath("icon-512.png"),
  appPath("apple-touch-icon.png"),
  appPath("stock-directory.json"),
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL_CACHE).then((cache) => cache.addAll(CORE_FILES)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    Promise.all([
      caches
        .keys()
        .then((keys) =>
          Promise.all(
            keys
              .filter((key) => key !== SHELL_CACHE && key !== ASSET_CACHE)
              .map((key) => caches.delete(key)),
          ),
        ),
      self.clients.claim(),
    ]),
  );
});

async function cacheCurrentShell() {
  const request = new Request(APP_URL, {
    credentials: "include",
    cache: "reload",
  });
  const response = await fetch(request);
  const contentType = response.headers.get("content-type") || "";
  if (
    response.ok &&
    !response.redirected &&
    response.type === "basic" &&
    contentType.includes("text/html")
  ) {
    const cache = await caches.open(SHELL_CACHE);
    await cache.put(APP_URL, response.clone());
  }
}

self.addEventListener("message", (event) => {
  if (event.data?.type === "SKIP_WAITING") {
    self.skipWaiting();
    return;
  }
  if (event.data?.type === "CACHE_APP_SHELL") {
    event.waitUntil(cacheCurrentShell().catch(() => undefined));
  }
});

async function navigationResponse(request) {
  try {
    const response = await fetch(request);
    const contentType = response.headers.get("content-type") || "";
    if (
      response.ok &&
      !response.redirected &&
      response.type === "basic" &&
      contentType.includes("text/html")
    ) {
      const cache = await caches.open(SHELL_CACHE);
      await cache.put(APP_URL, response.clone());
    }
    return response;
  } catch {
    return (
      (await caches.match(APP_URL)) ||
      (await caches.match(OFFLINE_URL)) ||
      Response.error()
    );
  }
}

async function staticAssetResponse(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok && response.type === "basic") {
    const cache = await caches.open(ASSET_CACHE);
    await cache.put(request, response.clone());
  }
  return response;
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (
    url.origin !== self.location.origin ||
    url.pathname.startsWith(appPath("api/"))
  )
    return;

  if (request.mode === "navigate") {
    event.respondWith(navigationResponse(request));
    return;
  }

  if (url.pathname === appPath("market-close.json")) {
    event.respondWith(fetch(new Request(request, { cache: "no-store" })));
    return;
  }

  if (
    url.pathname === appPath("stock-directory.json") ||
    ["style", "script", "font", "image"].includes(request.destination)
  )
    event.respondWith(staticAssetResponse(request));
});
