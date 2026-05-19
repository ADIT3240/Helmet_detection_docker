import { getDownloadUrl } from "../api";

export default function Results({ jobId, onReset }) {
  return (
    <div>
      <video
        src={getDownloadUrl(jobId)}
        controls
        autoPlay
        style={{ width: "100%", borderRadius: 12, background: "#000", display: "block" }}
      />

      <div style={{ display: "flex", gap: 12, marginTop: 16 }}>
        <a
          href={getDownloadUrl(jobId)}
          download
          style={{
            flex: 1, display: "block", textAlign: "center",
            background: "#6366f1", color: "#fff", fontWeight: 600,
            padding: "13px", borderRadius: 10, textDecoration: "none",
            fontSize: 15,
          }}
        >
          Download Video
        </a>
        <button
          onClick={onReset}
          style={{
            flex: 1, background: "#27272a", color: "#e4e4e7", border: "none",
            fontWeight: 600, padding: "13px", borderRadius: 10, cursor: "pointer",
            fontSize: 15,
          }}
        >
          Process Another Video
        </button>
      </div>
    </div>
  );
}
