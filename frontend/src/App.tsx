import { useEffect } from "react";
import { Onboarding } from "./routes/Onboarding";
import { Splash } from "./routes/Splash";
import { Feed } from "./routes/Feed";
import { useApp } from "./lib/store";

export default function App() {
  const stage = useApp((s) => s.stage);
  const error = useApp((s) => s.error);
  const hydrate = useApp((s) => s.hydrate);
  const resetSession = useApp((s) => s.resetSession);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  if (stage === "error") {
    return (
      <div className="min-h-[100dvh] flex flex-col items-center justify-center px-6 text-center gap-4">
        <div className="text-red-400 font-bold">Something broke.</div>
        <div className="text-xs text-muted max-w-md whitespace-pre-wrap">{error}</div>
        <button
          onClick={resetSession}
          className="mt-4 px-5 py-2.5 rounded-full bg-white text-ink font-semibold"
        >
          Start over
        </button>
      </div>
    );
  }
  if (stage === "warming") return <Splash />;
  if (stage === "feed") return <Feed />;
  return <Onboarding />;
}
