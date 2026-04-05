import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles.css";

// Limpiar tokens viejos que puedan causar problemas
// Esto fuerza re-login si hay tokens de versiones anteriores
const appVersion = "jwt-v4";
if (localStorage.getItem("app_version") !== appVersion) {
  localStorage.clear();
  localStorage.setItem("app_version", appVersion);
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
