import { useEffect, useMemo, useRef, useState } from "react";
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

  const lines = match[1]
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

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
  if (typeof status === "string" && status.toLowerCase().includes("confirm")) {
    return true;
  }

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
    if (posReady && latestOrderSummary) {
      return placedOrderId
        ? `Order #${placedOrderId} placed. POS receipt ready for ${latestOrderSummary.book}`
        : `POS receipt ready for ${latestOrderSummary.book}`;
    }
    if (latestOrderSummary) {
      return `Order summary captured for ${latestOrderSummary.book}`;
    }
    return "Ask for book reviews, negotiate pricing, or place your order here.";
  }, [latestOrderSummary, placedOrderId, posReady]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isOpen]);

  useEffect(() => {
    if (!openSignal) return;
    setIsOpen(true);
    setTimeout(() => textareaRef.current?.focus(), 0);
  }, [openSignal]);

  useEffect(() => {
    if (!selectedBook?.id) return;
    if (!token) return;
    setLatestOrderSummary(null);
    setPosReady(false);
    setPlacedOrderId(null);
    setSuccessOrder(null);
    const text = `Selected book: ${selectedBook.title}`;
    setIsOpen(true);
    void submitMessage(text, selectedBook.title);
  }, [selectedBook, token]);

  async function submitMessage(text, highlightedBook) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setMessages((current) => [
      ...current,
      {
        id: `user_${Date.now()}`,
        role: "user",
        text: highlightedBook ? `${trimmed}\n\nSelected book: ${highlightedBook}` : trimmed,
        rawText: trimmed,
      },
    ]);

    setLoading(true);
    try {
      const response = await sendAssistantMessageRequest({
        chatInput: trimmed,
        sessionId: buildSessionId(),
      });

      const reply = response.data.reply || "I could not generate a reply right now.";
      const parsedSummary = parseOrderSummary(reply);
      const orderSummary = parsedSummary || latestOrderSummary;
      let finalizedOrderId = placedOrderId;
      if (parsedSummary) {
        setLatestOrderSummary(parsedSummary);
      }
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
          if (orderResponse.data.order) {
            dispatch(upsertOrder(orderResponse.data.order));
          }
          await dispatch(fetchMyOrders()).unwrap();
          const successSummary = buildSuccessSummary(orderResponse.data, orderSummary);
          setSuccessOrder(successSummary);
          setLatestOrderSummary((current) => ({
            book: successSummary.book,
            quantity: successSummary.quantity,
            name: current?.name || orderSummary?.name || "Customer",
            phone: current?.phone || orderSummary?.phone || "-",
            address: current?.address || orderSummary?.address || "-",
            total: orderResponse.data.total,
          }));
          navigate("/orders");
          setPosReady(true);
        } else if (placedOrderId && latestOrderSummary) {
          setPosReady(true);
        }
      }

      setMessages((current) => [
        ...current,
        {
          id: `assistant_${Date.now()}`,
          role: "assistant",
          text: reply,
          rawText: reply,
        },
        ...(isOrderConfirmed(reply, response.data.status) && orderSummary
          ? [
              {
                id: `assistant_order_${Date.now()}`,
                role: "assistant",
                text: finalizedOrderId
                  ? `Order #${finalizedOrderId} has been placed in the bookstore system for ${orderSummary.book}.`
                  : "Your confirmed order has been placed in the bookstore system.",
                rawText: "Assistant order placement completed.",
              },
            ]
          : []),
      ]);
    } catch (error) {
      const message = getApiError(error, "Failed to reach the n8n webhook.");
      const fallbackMessage =
        message === "Failed to reach the n8n webhook."
          ? "The assistant could not complete your request right now."
          : message;
      setMessages((current) => [
        ...current,
        {
          id: `assistant_error_${Date.now()}`,
          role: "assistant",
          text: fallbackMessage,
          rawText: fallbackMessage,
        },
      ]);
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

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        className="fixed bottom-6 right-6 z-40 rounded-full bg-gradient-to-r from-bronze to-ember px-5 py-3 font-semibold text-white shadow-card"
      >
        {isOpen ? "Close assistant" : "Open assistant"}
      </button>

      {isOpen ? (
        <section className="fixed bottom-20 right-6 z-40 grid h-[82vh] w-[min(520px,calc(100vw-24px))] grid-rows-[auto_auto_1fr_auto] overflow-hidden rounded-[30px] border border-black/10 bg-white shadow-card">
          <header className="bg-gradient-to-r from-[#6b2f16] to-[#9f5f2b] px-5 py-4 text-white">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">AI Powered Bookstore Assistant</p>
            <h3 className="font-display text-3xl">Agent-led ordering</h3>
          </header>

          <div className="flex items-center justify-between gap-4 border-b border-black/5 bg-[#fff7ee] px-5 py-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bronze">Assistant Flow</p>
              <p className="mt-1 text-sm text-ink/70">{helperText}</p>
            </div>
            {posReady && latestOrderSummary ? (
              <button
                type="button"
                className="btn-secondary whitespace-nowrap"
                onClick={() => downloadPosPdf(latestOrderSummary)}
              >
                Download POS PDF
              </button>
            ) : null}
          </div>

          <div className="space-y-4 overflow-y-auto bg-[#fcfaf6] p-5">
            {!token ? (
              <article className="max-w-[92%] rounded-2xl border border-black/10 bg-white px-5 py-4 text-[15px] leading-7 text-ink">
                <p className="font-semibold">Login required for ordering</p>
                <p className="mt-2 text-sm text-ink/70">
                  Register or log in first. Only authenticated users can place orders with the assistant.
                </p>
                <div className="mt-4">
                  <Link to="/login" className="btn-primary">
                    Login to Continue
                  </Link>
                </div>
              </article>
            ) : (
              <>
                {successOrder ? (
                  <article className="max-w-[96%] rounded-3xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-ink">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700">Order Placed</p>
                    <h4 className="mt-2 font-display text-3xl">Order #{successOrder.orderId}</h4>
                    <div className="mt-3 grid gap-2 text-sm text-ink/75 sm:grid-cols-2">
                      <p>Book: {successOrder.book}</p>
                      <p>Quantity: {successOrder.quantity}</p>
                      <p>Total: ${successOrder.total}</p>
                      <p>Status: {successOrder.status}</p>
                    </div>
                    <p className="mt-3 text-sm text-ink/70">
                    The order is now saved in your account. You can review it in the Orders page.
                  </p>
                </article>
              ) : null}
                {messages.map((message) => (
                  <article
                    key={message.id}
                    className={`max-w-[88%] rounded-2xl border px-4 py-3 text-[15px] leading-7 ${
                      message.role === "assistant"
                        ? "border-black/10 bg-white text-ink"
                        : "ml-auto border-amber-200 bg-amber-100 text-ink"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.text}</p>
                  </article>
                ))}
                {loading ? (
                  <article className="max-w-[85%] rounded-2xl border border-black/10 bg-white px-4 py-3 text-sm text-ink/70">
                    The assistant is checking the book details, reviews, or order options...
                  </article>
                ) : null}
              </>
            )}
            <div ref={endRef} />
          </div>

          <form className="grid gap-3 border-t border-black/10 bg-white p-4" onSubmit={handleSubmit}>
            <textarea
              ref={textareaRef}
              className="input min-h-28 text-[15px] leading-7"
              placeholder="Ask for reviews, negotiate a price, or say 'place order' when you want checkout details..."
              value={input}
              onChange={(event) => setInput(event.target.value)}
              disabled={!token}
            />
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs text-ink/55">
                {token ? "You can ask for reviews, negotiate, and complete the order here." : "Login is required before ordering."}
              </p>
              <button type="submit" className="btn-primary justify-self-end disabled:cursor-not-allowed disabled:opacity-50" disabled={!token}>
                Send
              </button>
            </div>
          </form>
        </section>
      ) : null}
    </>
  );
}
