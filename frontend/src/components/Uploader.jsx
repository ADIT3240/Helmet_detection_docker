import { useRef, useState } from "react";

export default function Uploader({ onUpload }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  function handleFile(file) {
    if (!file || !file.type.startsWith("video/")) {
      alert("Please select a video file.");
      return;
    }
    onUpload(file);
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  }

  return (
    <div
      onClick={() => inputRef.current.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      style={{
        border: `2px dashed ${dragging ? "#6366f1" : "#3f3f46"}`,
        borderRadius: 16,
        padding: "60px 40px",
        textAlign: "center",
        cursor: "pointer",
        background: dragging ? "#1e1b4b22" : "#18181b",
        transition: "all 0.2s",
      }}
    >
      <div style={{ fontSize: 48, marginBottom: 16 }}>🎥</div>
      <p style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>
        Drop your video here
      </p>
      <p style={{ color: "#71717a", fontSize: 14 }}>
        or click to browse — MP4, MOV, AVI supported
      </p>
      <input
        ref={inputRef}
        type="file"
        accept="video/*"
        style={{ display: "none" }}
        onChange={(e) => handleFile(e.target.files[0])}
      />
    </div>
  );
}
