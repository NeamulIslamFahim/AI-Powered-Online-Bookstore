import { useEffect, useRef, useState, useCallback } from "react";
import { sendAdminChatRequest } from "../api/adminApi";
import { useNavigate } from "react-router-dom";

const MIN_W = 320;
const MAX_W = 900;
const MIN_H = 380;
const MAX_H = window.innerHeight - 100;
const DEFAULT_W = 420;
const DEFAULT_H = Math.min(580, window.innerHeight - 140);

export default function AdminChatbotWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([{
    id: "welcome", role: "assistant", text:
      "Hello Admin 👋 I can help you:\n" +
      "• Navigate: 'go to users', 'manage books'\n" +
      "• Add a book: 'add book Dune by Frank Herbert, price 12.99, stock 50, category Fiction'\n" +
      "• Edit a book: 'change the price of Atomic Habits to 25'\n" +
      "• Delete a book: 'delete The Great Gatsby'\n\n" +
      "Just tell me what you need naturally!"
  }]);
  const [loading, setLoading] = useState(false);
  const [imageUrl, setImageUrl] = useState("");
  const [imageName, setImageName] = useState("");
  const [size, setSize] = useState({ w: DEFAULT_W, h: DEFAULT_H });
  const endRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const sessionIdRef = useRef(crypto.randomUUID());
  const navigate = useNavigate();
  const dragRef = useRef(null);

  const handleImageUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleImageChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setImageName(file.name);
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        setImageUrl(reader.result);
      }
    };
    reader.readAsDataURL(file);
  };

  const handleClearImage = () => {
    setImageUrl("");
    setImageName("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isOpen]);

  // ── Resize drag logic ──────────────────────────────────────────────────────
  const startResize = useCallback((e) => {
    e.preventDefault();
    const startX = e.clientX;
    const startY = e.clientY;
    const startW = size.w;
    const startH = size.h;

    function onMove(ev) {
      const newW = Math.min(MAX_W, Math.max(MIN_W, startW - (ev.clientX - startX)));
      const newH = Math.min(MAX_H, Math.max(MIN_H, startH - (ev.clientY - startY)));
      setSize({ w: newW, h: newH });
    }
    function onUp() {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [size]);

  async function handleSubmit(event) {
    event.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((c) => [...c, { id: `user_${Date.now()}`, role: "user", text }]);
    setLoading(true);
    try {
      const response = await sendAdminChatRequest({
        message: text,
        session_id: sessionIdRef.current,
        image_url: imageUrl || undefined,
      });
      const data = response.data;
      setMessages((c) => [...c, {
        id: `assistant_${Date.now()}`,
        role: "assistant",
        text: data.reply,
        coverImage: data.image_url || null,
      }]);
      if (data.action === "NAVIGATE" && data.target) {
        setTimeout(() => navigate(data.target), 1500);
      }
    } catch {
      setMessages((c) => [...c, { id: `err_${Date.now()}`, role: "assistant", text: "Sorry, I encountered an error executing your command." }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen((c) => !c)}
        className="fixed bottom-6 left-6 z-40 rounded-full bg-gradient-to-r from-emerald-600 to-teal-600 px-5 py-3 font-semibold text-white shadow-card"
      >
        {isOpen ? "Close Admin Assistant" : "Admin Assistant"}
      </button>

      {isOpen && (
        <section
          style={{ width: size.w, height: size.h }}
          className="fixed bottom-20 left-6 z-40 grid grid-rows-[auto_1fr_auto] overflow-hidden rounded-[30px] border border-black/10 bg-white shadow-card"
        >
          {/* Resize handle — top-left corner */}
          <div
            ref={dragRef}
            onMouseDown={startResize}
            className="absolute top-0 left-0 z-50 h-6 w-6 cursor-nw-resize rounded-tl-[30px]"
            title="Drag to resize"
            style={{
              background: "linear-gradient(135deg, rgba(16,185,129,0.4) 40%, transparent 60%)",
            }}
          />

          <header className="bg-gradient-to-r from-emerald-700 to-teal-700 px-5 py-4 text-white select-none">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">Admin Controller</p>
                <h3 className="font-display text-2xl">Command Center</h3>
              </div>
              <span className="text-xs text-white/50 cursor-nw-resize select-none">↔ drag corner to resize</span>
            </div>
          </header>

          <div className="space-y-4 overflow-y-auto bg-[#f4fbfa] p-5">
            {messages.map((message) => (
              <article
                key={message.id}
                className={`max-w-[88%] rounded-2xl border px-4 py-3 text-[14px] leading-6 ${
                  message.role === "assistant"
                    ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                    : "ml-auto border-black/10 bg-white text-ink"
                }`}
              >
                {message.coverImage && (
                  <div style={{ marginBottom: "10px" }}>
                    <img
                      src={message.coverImage}
                      alt="Book cover"
                      style={{
                        width: "100%",
                        maxWidth: "180px",
                        height: "auto",
                        borderRadius: "10px",
                        boxShadow: "0 4px 16px rgba(0,0,0,0.18)",
                        display: "block",
                        margin: "0 auto 6px auto",
                        border: "2px solid #a7f3d0",
                      }}
                      onError={(e) => { e.currentTarget.style.display = "none"; }}
                    />
                    <p style={{ textAlign: "center", fontSize: "11px", color: "#6b7280", margin: 0 }}>Book Cover</p>
                  </div>
                )}
                <p className="whitespace-pre-wrap">{message.text}</p>
              </article>
            ))}
            {loading && (
              <article className="max-w-[85%] rounded-2xl border border-black/10 bg-white px-4 py-3 text-sm text-ink/70">
                Executing command...
              </article>
            )}
            <div ref={endRef} />
          </div>

          <form className="grid gap-3 border-t border-black/10 bg-white p-4" onSubmit={handleSubmit}>
            <div className="flex items-end gap-3">
              <button
                type="button"
                onClick={handleImageUploadClick}
                className="btn-ghost rounded px-3 py-2"
                title="Attach cover image"
              >
                <span className="text-lg">📎</span>
              </button>

              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleImageChange}
              />

              <textarea
                ref={textareaRef}
                className="input flex-1 min-h-[72px] text-[14px] leading-6"
                placeholder="e.g. 'delete Dune' or 'change price of Atomic Habits to 25'..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
              />

              <button type="submit" className="btn-primary px-4 py-2">
                Send
              </button>
            </div>

            {imageName && (
              <div className="mt-2 flex items-center justify-between">
                <p className="text-xs text-ink/80">Selected image: {imageName}</p>
                <button type="button" className="text-xs text-ink/70 underline" onClick={handleClearImage}>
                  Clear
                </button>
              </div>
            )}
            <p className="text-xs text-ink/60 mt-1">
              Attach a cover image for the next book entry. If none is provided, the assistant will generate one.
            </p>
          </form>
        </section>
      )}
    </>
  );
}
