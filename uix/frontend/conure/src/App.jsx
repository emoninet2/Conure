import Home from "./pages/Home";
import Landing from "./pages/Landing";
import { useUiStore } from "./state/uiStore";

function App() {
  const page = useUiStore((s) => s.getValue(["nav", "page"], "landing"));
  const setValue = useUiStore((s) => s.setValue);

  // Note: we do NOT auto-load state.json here anymore.
  // Landing will call load() after a project is opened.

  if (page === "home") {
    return <Home onBack={() => setValue(["nav", "page"], "landing")} />;
  }

  return <Landing />;
}

export default App;
