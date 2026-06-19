import { createRoot } from "react-dom/client";
import { ProductViewerApp } from "./app/ProductViewerApp.js";

const mountPoint = typeof document === "undefined" ? null : document.getElementById("app");

if (mountPoint !== null) {
  createRoot(mountPoint).render(<ProductViewerApp />);
}

