import { useState } from "react";
import { uploadVideo } from "./api";
import Uploader from "./components/Uploader";
import Progress from "./components/Progress";
import Results from "./components/Results";

// States: idle → uploading → processing → done | error
export default function App() {
  const [stage, setStage] = useState("idle");
  const [jobId, setJobId] = useState(null);
  const [error, setError] = useState(null);

  async function handleUpload(file) {
    setStage("uploading");
    setError(null);
    try {
      const { job_id } = await uploadVideo(file);
      setJobId(job_id);
      setStage("processing");
    } catch (e) {
      setError(e.message);
      setStage("error");
    }
  }

  function reset() {
    setStage("idle");
    setJobId(null);
    setError(null);
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 24 }}>
      <div style={{ width: "100%", maxWidth: stage === "done" ? 1000 : 540, transition: "max-width 0.3s ease" }}>
        {stage !== "done" && (
          <header style={{ textAlign: "center", marginBottom: 40 }}>
            <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: -0.5, marginBottom: 6 }}>
              🪖 Helmet Detection
            </h1>
            <p style={{ color: "#71717a", fontSize: 15 }}>
              Upload a traffic video — get back an annotated clip showing helmet compliance
            </p>
          </header>
        )}

        <div style={{ background: "#111113", border: "1px solid #27272a", borderRadius: 20, padding: 32 }}>
          {stage === "idle" && <Uploader onUpload={handleUpload} />}

          {stage === "uploading" && (
            <div style={{ textAlign: "center", padding: "40px 0" }}>
              <p style={{ fontWeight: 600, fontSize: 16 }}>Uploading video...</p>
            </div>
          )}

          {stage === "processing" && (
            <Progress
              jobId={jobId}
              onDone={() => setStage("done")}
              onError={(msg) => { setError(msg); setStage("error"); }}
            />
          )}

          {stage === "done" && <Results jobId={jobId} onReset={reset} />}

          {stage === "error" && (
            <div style={{ textAlign: "center", padding: "40px 0" }}>
              <div style={{ fontSize: 40, marginBottom: 16 }}>⚠️</div>
              <p style={{ fontWeight: 600, fontSize: 16, marginBottom: 8 }}>Something went wrong</p>
              <p style={{ color: "#ef4444", fontSize: 13, marginBottom: 24 }}>{error}</p>
              <button
                onClick={reset}
                style={{ background: "#27272a", color: "#e4e4e7", border: "none", padding: "12px 28px", borderRadius: 8, cursor: "pointer", fontWeight: 600 }}
              >
                Try Again
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
