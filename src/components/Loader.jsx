export default function Loader({ text = "Loading..." }) {
  return (
    <div className="flex items-center justify-center py-14">
      <div className="flex items-center gap-3 rounded-full bg-white/80 px-5 py-3 shadow-card">
        <span className="h-3 w-3 animate-pulse rounded-full bg-bronze" />
        <span className="text-sm font-medium text-ink/70">{text}</span>
      </div>
    </div>
  );
}

