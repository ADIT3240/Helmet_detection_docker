import { useEffect } from "react";
import { getStatus } from "../api";

export default function Progress({ jobId, onDone, onError }) {
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const data = await getStatus(jobId);
        if (data.status === "done") {
          clearInterval(interval);
          onDone(data.progress);
        } else if (data.status === "error") {
          clearInterval(interval);
          onError(data.message || "Processing failed");
        }
      } catch (e) {
        clearInterval(interval);
        onError(e.message);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [jobId]);

  return (
    <div style={{ textAlign: "center", padding: "40px 0" }}>
      <div style={{ marginBottom: 24 }}>
        <Spinner />
      </div>
      <p style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>
        Processing video...
      </p>
      <p style={{ color: "#71717a", fontSize: 14 }}>
        Running two-stage YOLO detection. This may take a moment.
      </p>
    </div>
  );
}

function Spinner() {
  return (
    <div style={{
      width: 48, height: 48, border: "4px solid #27272a",
      borderTop: "4px solid #6366f1", borderRadius: "50%",
      animation: "spin 0.9s linear infinite", margin: "0 auto",
    }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
