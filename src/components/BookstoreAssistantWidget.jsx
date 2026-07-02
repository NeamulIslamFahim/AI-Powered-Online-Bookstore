import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import { confirmAssistantOrderRequest, sendAssistantMessageRequest } from "../api/chatApi";
import { fetchMyOrders, upsertOrder } from "../features/orders/orderSlice";
import { getApiError } from "../utils/apiError";
import { downloadPosPdf } from "../utils/posPdf";

const welcomeMessage =
  "Hello! I'm your bookstore assistant. Ask about any book, request reader reviews, negotiate the price, and I can guide the order through checkout and receipt generation.";

function buildSessionId() {
  const existing = sessionStorage.getItem("assistant_session_id");
  if (existing) return existing;
  const created = `assistant_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
  sessionStorage.setItem("assistant_session_id", created);
  return created;
}

function parseOrderSummary(text) {
  const match = text.match(/ORDER SUMMARY:\s*([\s\S]*?)(?:Please confirm|Reply YES|Reply CONFIRM|$)/i);
  if (!match) return null;
  const lines = match[1].split("\n").map((l) => l.trim()).filter(Boolean);
  const summary = {};
  for (const line of lines) {
    const [label, ...rest] = line.split(":");
    if (!label || rest.length === 0) continue;
    summary[label.trim().toLowerCase()] = rest.join(":").trim();
  }
  return {
    book: summary.book || summary.books || summary.product || "Book order",
    quantity: Number(summary.quantity || "1"),
    name: summary.name || summary.customer || summary["customer name"] || "Customer",
    phone: summary.phone || "-",
    address: summary.address || "-",
    total: summary.total || "-",
  };
}

function isOrderConfirmed(reply, status) {
  if (typeof status === "string" && status.toLowerCase().includes("confirm")) return true;
  return /order confirmed|confirmed successfully|your order is confirmed/i.test(reply);
}

export default function BookstoreAssistantWidget({ openSignal, selectedBook }) {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { token } = useSelector((state) => state.auth);

  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([{ id: "welcome", role: "assistant", text: welcomeMessage, rawText: welcomeMessage }]);
  const [loading, setLoading] = useState(false);
  const [latestOrderSummary, setLatestOrderSummary] = useState(null);
  const [posReady, setPosReady] = useState(false);
  const [placedOrderId, setPlacedOrderId] = useState(null);
  const [successOrder, setSuccessOrder] = useState(null);

  const endRef = useRef(null);
  const textareaRef = useRef(null);

  // ── Resize ───────────────────────────────────────────────────────────────
  const MIN_W = 360, MAX_W = Math.min(1100, window.innerWidth - 32);
  const MIN_H = 460, MAX_H = window.innerHeight - 100;
  const DEFAULT_W = Math.min(560, window.innerWidth - 32);
  const DEFAULT_H = Math.min(Math.floor(window.innerHeight * 0.82), MAX_H);
  const [size, setSize] = useState({ w: DEFAULT_W, h: DEFAULT_H });
  const sizeRef = useRef(size);
  sizeRef.current = size;

  const startResize = useCallback((e) => {
    e.preventDefault();
    const startX = e.clientX;
    const startY = e.clientY;
    const { w: startW, h: startH } = sizeRef.current;
    function onMove(ev) {
      // right-anchored: drag right → wider; drag left → narrower
      const newW = Math.min(MAX_W, Math.max(MIN_W, startW + (ev.clientX - startX)));
      // drag up → taller; drag down → shorter
      const newH = Math.min(MAX_H, Math.max(MIN_H, startH - (ev.clientY - startY)));
      setSize({ w: newW, h: newH });
    }
    function onUp() {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, []);

  // ── Helpers ──────────────────────────────────────────────────────────────
  function buildSuccessSummary(orderResponse, fallbackSummary) {
    const items = orderResponse?.order?.items || [];
    const itemCount = items.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
    const bookLabel =
      items.length > 1
        ? items.map((item) => item.book?.title).filter(Boolean).join(", ")
        : items[0]?.book?.title || fallbackSummary?.book || "Book order";
    return {
      orderId: orderResponse.order_id,
      book: bookLabel,
      quantity: itemCount || fallbackSummary?.quantity || 1,
      total: orderResponse.total,
      status: orderResponse.status,
    };
  }

  const helperText = useMemo(() => {
    if (posReady && latestOrderSummary)
      return placedOrderId
        ? `Order #${placedOrderId} placed. POS receipt ready for ${latestOrderSummary.book}`
        : `POS receipt ready for ${latestOrderSummary.book}`;
    if (latestOrderSummary) return `Order summary captured for ${latestOrderSummary.book}`;
    return "Ask for book reviews, negotiate pricing, or place your order here.";
  }, [latestOrderSummary, placedOrderId, posReady]);

  // ── Effects ──────────────────────────────────────────────────────────────
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isOpen]);

  useEffect(() => {
    if (!openSignal) return;
    setIsOpen(true);
    setTimeout(() => textareaRef.current?.focus(), 50);
  }, [openSignal]);

  useEffect(() => {
    if (!selectedBook?.id || !token) return;
    setLatestOrderSummary(null);
    setPosReady(false);
    setPlacedOrderId(null);
    setSuccessOrder(null);
    setIsOpen(true);
    void submitMessage(`Selected book: ${selectedBook.title}`, selectedBook.title);
  }, [selectedBook, token]);

  // ── Message submission ───────────────────────────────────────────────────
  async function submitMessage(text, highlightedBook) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setMessages((c) => [
      ...c,
      {
        id: `user_${Date.now()}`,
        role: "user",
        text: highlightedBook ? `${trimmed}\n\nSelected book: ${highlightedBook}` : trimmed,
        rawText: trimmed,
      },
    ]);

    setLoading(true);
    try {
      const response = await sendAssistantMessageRequest({ chatInput: trimmed, sessionId: buildSessionId() });
      const reply = response.data.reply || "I could not generate a reply right now.";
      const parsedSummary = parseOrderSummary(reply);
      const orderSummary = parsedSummary || latestOrderSummary;
      let finalizedOrderId = placedOrderId;
      if (parsedSummary) setLatestOrderSummary(parsedSummary);

      if (isOrderConfirmed(reply, response.data.status)) {
        if (!placedOrderId) {
          const sessionId = buildSessionId();
          const orderResponse = await confirmAssistantOrderRequest({
            sessionId,
            book: orderSummary?.book,
            quantity: orderSummary?.quantity,
            name: orderSummary?.name,
            phone: orderSummary?.phone,
            address: orderSummary?.address,
          });
          finalizedOrderId = orderResponse.data.order_id;
          setPlacedOrderId(orderResponse.data.order_id);
          if (orderResponse.data.order) dispatch(upsertOrder(orderResponse.data.order));
          await dispatch(fetchMyOrders()).unwrap();
          const ss = buildSuccessSummary(orderResponse.data, orderSummary);
          setSuccessOrder(ss);
          setLatestOrderSummary((c) => ({
            book: ss.book, quantity: ss.quantity,
            name: c?.name || orderSummary?.name || "Customer",
            phone: c?.phone || orderSummary?.phone || "-",
            address: c?.address || orderSummary?.address || "-",
            total: orderResponse.data.total,
          }));
          navigate("/orders");
          setPosReady(true);
        } else if (placedOrderId && latestOrderSummary) {
          setPosReady(true);
        }
      }

      setMessages((c) => [
        ...c,
        { id: `assistant_${Date.now()}`, role: "assistant", text: reply, rawText: reply },
        ...(isOrderConfirmed(reply, response.data.status) && orderSummary
          ? [{ id: `assistant_order_${Date.now()}`, role: "assistant",
              text: finalizedOrderId
                ? `Order #${finalizedOrderId} has been placed in the bookstore system for ${orderSummary.book}.`
                : "Your confirmed order has been placed in the bookstore system.",
              rawText: "Assistant order placement completed." }]
          : []),
      ]);
    } catch (error) {
      const msg = getApiError(error, "Failed to reach the n8n webhook.");
      const fallback = msg === "Failed to reach the n8n webhook."
        ? "The assistant could not complete your request right now." : msg;
      setMessages((c) => [...c, { id: `err_${Date.now()}`, role: "assistant", text: fallback, rawText: fallback }]);
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const text = input;
    setInput("");
    await submitMessage(text);
  }

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <>
      {/* Toggle button */}
      <button
        type="button"
        onClick={() => setIsOpen((c) => !c)}
        className="fixed bottom-6 right-6 z-40 rounded-full bg-gradient-to-r from-bronze to-ember px-5 py-3 font-semibold text-white shadow-card"
      >
        {isOpen ? "Close assistant" : "Open assistant"}
      </button>

      {isOpen && (
        <section
          style={{ width: size.w, height: size.h }}
          className="fixed bottom-20 right-6 z-40 flex flex-col overflow-hidden rounded-[28px] border border-black/10 bg-white shadow-[0_24px_80px_rgba(0,0,0,0.18)]"
        >
          {/* ── Resize handle — full-width top bar ── */}
          <div
            onMouseDown={startResize}
            className="absolute top-0 left-0 right-0 h-3 cursor-n-resize z-50 flex items-center justify-center"
            style={{ background: "rgba(0,0,0,0.04)", borderRadius: "28px 28px 0 0" }}
            title="Drag to resize"
          >
            <div className="w-12 h-1 rounded-full bg-black/20" />
          </div>

          {/* ── Header ── */}
          <header className="flex-none bg-gradient-to-r from-[#6b2f16] to-[#9f5f2b] px-6 pt-6 pb-4 text-white">
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-white/60">AI Powered Bookstore Assistant</p>
            <h3 className="mt-1 font-display text-2xl leading-tight">Agent-led ordering</h3>
          </header>

          {/* ── Status bar ── */}
          <div className="flex-none flex items-center justify-between gap-3 border-b border-black/5 bg-[#fff7ee] px-5 py-3">
            <p className="text-[13px] text-amber-800 truncate">{helperText}</p>
            {posReady && latestOrderSummary && (
              <button type="button" className="btn-secondary whitespace-nowrap text-sm py-2 px-4"
                onClick={() => downloadPosPdf(latestOrderSummary)}>
                Download POS PDF
              </button>
            )}
          </div>

          {/* ── Messages area — takes all remaining height ── */}
          <div className="flex-1 min-h-0 overflow-y-auto bg-[#faf8f4] px-5 py-5 space-y-4">
            {!token ? (
              <article className="rounded-2xl border border-black/10 bg-white px-5 py-5 text-[15px] leading-7 text-ink">
                <p className="font-semibold text-base">Login required for ordering</p>
                <p className="mt-2 text-sm text-ink/70">
                  Register or log in first. Only authenticated users can place orders with the assistant.
                </p>
                <div className="mt-4">
                  <Link to="/login" className="btn-primary">Login to Continue</Link>
                </div>
              </article>
            ) : (
              <>
                {successOrder && (
                  <article className="rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-ink">
                    <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-600">Order Placed</p>
                    <h4 className="mt-1 font-display text-2xl">Order #{successOrder.orderId}</h4>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-sm text-ink/75">
                      <p>Book: {successOrder.book}</p>
                      <p>Qty: {successOrder.quantity}</p>
                      <p>Total: ${successOrder.total}</p>
                      <p>Status: {successOrder.status}</p>
                    </div>
                    <p className="mt-3 text-sm text-ink/60">The order is saved in your account.</p>
                  </article>
                )}

                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === "assistant" ? "justify-start" : "justify-end"}`}
                  >
                    {msg.role === "assistant" && (
                      <div className="mr-2 mt-1 h-7 w-7 flex-none rounded-full bg-gradient-to-br from-bronze to-ember flex items-center justify-center text-white text-xs font-bold select-none">
                        AI
                      </div>
                    )}
                    <article
                      className={`max-w-[80%] rounded-2xl px-4 py-3 text-[14.5px] leading-[1.65] shadow-sm ${
                        msg.role === "assistant"
                          ? "bg-white border border-black/8 text-ink rounded-tl-sm"
                          : "bg-amber-500 text-white rounded-tr-sm"
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.text}</p>
                    </article>
                  </div>
                ))}

                {loading && (
                  <div className="flex justify-start">
                    <div className="mr-2 mt-1 h-7 w-7 flex-none rounded-full bg-gradient-to-br from-bronze to-ember flex items-center justify-center text-white text-xs font-bold">AI</div>
                    <article className="rounded-2xl rounded-tl-sm bg-white border border-black/8 px-4 py-3 text-sm text-ink/60 shadow-sm">
                      <span className="inline-flex gap-1 items-center">
                        <span className="animate-bounce delay-0">●</span>
                        <span className="animate-bounce delay-75">●</span>
                        <span className="animate-bounce delay-150">●</span>
                      </span>
                    </article>
                  </div>
                )}
                <div ref={endRef} />
              </>
            )}
          </div>

          {/* ── Input form ── */}
          <form
            className="flex-none border-t border-black/8 bg-white px-4 py-3"
            onSubmit={handleSubmit}
          >
            <div className="flex items-end gap-2">
              <textarea
                ref={textareaRef}
                rows={2}
                className="flex-1 resize-none rounded-2xl border border-black/10 bg-[#faf8f4] px-4 py-3 text-[14.5px] leading-6 outline-none transition focus:border-bronze focus:ring-2 focus:ring-bronze/20 disabled:opacity-50"
                placeholder={token ? "Ask for reviews, negotiate a price, or say 'place order'..." : "Login to chat"}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={!token}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(e); }
                }}
              />
              <button
                type="submit"
                disabled={!token || !input.trim()}
                className="flex-none rounded-2xl bg-gradient-to-r from-bronze to-ember px-5 py-3 font-semibold text-white shadow-sm transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Send
              </button>
            </div>
            {!token && (
              <p className="mt-2 text-center text-xs text-ink/50">Login is required before you can chat.</p>
            )}
          </form>
        </section>
      )}
    </>
  );
}
