import ReactDOM from "react-dom/client";
import Root from "./Root";
import { ThemeProvider } from "./ThemeContext";
import "./index.css";
import "./charts/ChartjsConfig";

// No StrictMode: in dev it double-invokes effects (every API call -- and
// every Groq-backed call with it -- fires twice per mount), which was
// eating into Groq's free-tier daily request cap for no demo benefit.
ReactDOM.createRoot(document.getElementById("root")!).render(
  <ThemeProvider>
    <Root />
  </ThemeProvider>
);
