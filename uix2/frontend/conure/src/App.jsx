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


// import { useEffect } from "react";
// import Home from "./pages/Home";
// import { useUiStore } from "./state/uiStore";

// function App() {
//   const load = useUiStore((s) => s.load);
//   const loaded = useUiStore((s) => s.loaded);
//   const page = useUiStore((s) => s.getValue(["nav", "page"], "landing"));
//   const setValue = useUiStore((s) => s.setValue);

//   useEffect(() => {
//     load();
//   }, [load]);

//   if (!loaded) {
//     return <div style={{ padding: 16 }}>Loading...</div>;
//   }

//   if (page === "home") {
//     return <Home onBack={() => setValue(["nav", "page"], "landing")} />;
//   }

//   return (
//     <div style={{ padding: 16 }}>
//       <h1>Landing</h1>
//       <button onClick={() => setValue(["nav", "page"], "home")}>Start</button>
//     </div>
//   );
// }

// export default App;