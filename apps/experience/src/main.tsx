import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@design-tokens.css";
import "./styles.css";
import { App } from "./App";

const root = document.getElementById("root");
if (!root) throw new Error("Experience root is missing.");
createRoot(root).render(<StrictMode><App /></StrictMode>);
