import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { createProvider } from "./data/provider";
import { CSS } from "./styles";

const style = document.createElement("style");
style.textContent = CSS;
document.head.appendChild(style);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App provider={createProvider()} />
  </StrictMode>,
);
