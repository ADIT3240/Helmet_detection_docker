const BASE = import.meta.env.VITE_API_BASE || "/api";

export async function uploadVideo(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/jobs`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json(); // { job_id }
}

export async function getStatus(jobId) {
  const res = await fetch(`${BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json(); // { job_id, status, progress, message }
}

export async function getStats(jobId) {
  const res = await fetch(`${BASE}/jobs/${jobId}/stats`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function getDownloadUrl(jobId) {
  return `${BASE}/jobs/${jobId}/download`;
}
