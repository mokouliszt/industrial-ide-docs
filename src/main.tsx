import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { PreloadContext } from "./lib/preload";
import "./index.css";

const preload = window.__PRELOAD__ ?? null;
const rootEl = document.getElementById("root")!;
const app = (
  <React.StrictMode>
    <PreloadContext.Provider value={preload}>
      <App />
    </PreloadContext.Provider>
  </React.StrictMode>
);

if (rootEl.hasChildNodes()) {
  ReactDOM.hydrateRoot(rootEl, app);
} else {
  ReactDOM.createRoot(rootEl).render(app);
}
