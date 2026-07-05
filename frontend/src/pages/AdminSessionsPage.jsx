import { useEffect, useState } from "react";
import { fetchAdminSessionsRequest, deleteAdminSessionRequest } from "../api/adminApi";
import Alert from "../components/Alert";
import Loader from "../components/Loader";
import { formatPrice } from "../utils/formatters";

export default function AdminSessionsPage() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadSessions();
  }, []);

  async function loadSessions() {
    try {
      setLoading(true);
      const res = await fetchAdminSessionsRequest();
      setSessions(res.data);
    } catch (err) {
      setError("Failed to load sessions.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(sessionId) {
    if (!window.confirm("Are you sure you want to delete this session?")) return;
    try {
      await deleteAdminSessionRequest(sessionId);
      setSessions(sessions.filter(s => s.session_id !== sessionId));
    } catch (err) {
      alert("Failed to delete session");
    }
  }

  if (loading) return <Loader text="Loading sessions..." />;

  return (
    <div className="space-y-8 py-8">
      <section className="surface p-8">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bronze">Admin Sessions</p>
            <h1 className="mt-3 font-display text-5xl">Active Customer Sessions</h1>
          </div>
        </div>

        <div className="mt-6">
          <Alert message={error} />
        </div>

        <div className="mt-8 space-y-4">
          {!sessions.length ? <p className="text-sm text-ink/60">No active assistant sessions found.</p> : null}
          {sessions.map((s) => (
            <div key={s.session_id} className="rounded-3xl bg-mist p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h3 className="font-semibold text-lg">Session: {s.session_id}</h3>
                  <p className="text-sm text-ink/60 mt-1">User: {s.user?.name} ({s.user?.email})</p>
                  <p className="text-sm text-ink/60 mt-1">State: <span className="font-bold text-ink">{s.state}</span></p>
                  <p className="text-xs text-ink/50 mt-1">Started: {new Date(s.created_at).toLocaleString()}</p>
                  
                  {s.items && s.items.length > 0 && (
                    <div className="mt-3">
                      <p className="text-xs font-semibold uppercase text-bronze">Items in session:</p>
                      <ul className="list-disc list-inside text-sm text-ink/80 mt-1">
                        {s.items.map(item => (
                          <li key={item.id}>
                            Book ID {item.book_id} (Qty: {item.quantity || 0}) 
                            {item.negotiated_unit_price && ` @ ${formatPrice(item.negotiated_unit_price)}`}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
                <div className="flex gap-3">
                  <button type="button" className="btn-primary" onClick={() => handleDelete(s.session_id)}>
                    Terminate Session
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
