export default function Modal({ open, title, children, onClose }) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center overflow-y-auto bg-ink/40 px-4 py-6">
      <div className="surface flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden">
        <div className="mb-5 flex items-center justify-between border-b border-black/5 px-6 pb-5 pt-6">
          <h3 className="font-display text-3xl text-ink">{title}</h3>
          <button type="button" className="btn-secondary px-4 py-2" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="overflow-y-auto px-6 pb-6">{children}</div>
      </div>
    </div>
  );
}
