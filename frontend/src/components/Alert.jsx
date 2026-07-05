export default function Alert({ type = "error", message }) {
  if (!message) return null;

  const tones = {
    error: "border-red-200 bg-red-50 text-red-700",
    success: "border-emerald-200 bg-emerald-50 text-emerald-700",
    info: "border-sky-200 bg-sky-50 text-sky-700",
  };

  return <div className={`rounded-2xl border px-4 py-3 text-sm ${tones[type]}`}>{message}</div>;
}

