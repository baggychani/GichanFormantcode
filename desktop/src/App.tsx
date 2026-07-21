import "./App.css";
import { lazy, Suspense } from "react";
import { MainWorkspace } from "./components/mainWorkspace/MainWorkspace";

const InteractivePlotWindow = lazy(async () => {
  const module = await import("./components/InteractivePlotWindow");
  return { default: module.InteractivePlotWindow };
});

export default function App() {
  if (window.location.hash === "#single-plot") {
    return (
      <Suspense fallback={<div className="window-loading">플롯 창을 여는 중…</div>}>
        <InteractivePlotWindow />
      </Suspense>
    );
  }
  return <MainWorkspace />;
}
