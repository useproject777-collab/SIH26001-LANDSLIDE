import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

// Do not install a service worker during Vite development. Remove any older
// project service worker/cache so stale React bundles cannot hide code changes.
if (import.meta.env.DEV && "serviceWorker" in navigator) {
  navigator.serviceWorker.getRegistrations().then(async (registrations) => {
    if (!registrations.length) return;
    await Promise.all(registrations.map((registration) => registration.unregister()));
    if ("caches" in window) {
      const keys = await caches.keys();
      await Promise.all(keys.filter((key) => key.startsWith("ner-landslide-")).map((key) => caches.delete(key)));
    }
  }).catch(() => {});
}

if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}
