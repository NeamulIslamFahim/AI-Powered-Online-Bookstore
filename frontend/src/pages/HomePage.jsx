import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import Alert from "../components/Alert";
import BookCard from "../components/BookCard";
import Loader from "../components/Loader";
import { fetchBooksRequest } from "../api/booksApi";
import { addWishlist } from "../features/wishlist/wishlistSlice";
import { getApiError } from "../utils/apiError";

export default function HomePage({ onOpenAssistant, onSelectBook }) {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = useSelector((state) => state.auth);
  const [topBooks, setTopBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;

    fetchBooksRequest({ page: 1, limit: 4, sort: "best_selling" })
      .then((response) => {
        if (!active) return;
        setTopBooks(response.data.items || []);
        setError(null);
      })
      .catch((requestError) => {
        if (!active) return;
        setError(getApiError(requestError, "Failed to load top-selling books"));
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  function handleAskAssistant(book) {
    if (!token) {
      navigate("/login", { state: { from: location } });
      return;
    }

    onSelectBook(book);
    onOpenAssistant();
  }

  return (
    <div className="space-y-10 py-8">
      <section className="surface grid gap-8 p-8 md:grid-cols-[1.2fr_0.8fr]">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-bronze">Online Bookstore</p>
          <h1 className="mt-4 font-display text-6xl leading-none text-ink">Let readers discover your most sold books first.</h1>
          <p className="mt-6 max-w-2xl text-base leading-8 text-ink/70">
            The homepage now highlights top-selling titles, while the full catalog lives in the dedicated Book List page.
            Readers can move from discovery to assistant-led ordering in one clear flow.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/books" className="btn-primary">
              Explore Book List
            </Link>
            <button type="button" className="btn-secondary" onClick={onOpenAssistant}>
              Open Assistant
            </button>
          </div>
        </div>
        <div className="rounded-[28px] bg-gradient-to-br from-[#5f2d18] to-[#24140c] p-8 text-white shadow-card">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">Homepage focus</p>
          <div className="mt-4 space-y-4 text-sm leading-7 text-white/80">
            <p>Show the best-selling books first to build trust and momentum.</p>
            <p>Send users to Book List when they want the full catalog and filters.</p>
            <p>Keep ordering conversational through the assistant instead of a manual checkout flow.</p>
          </div>
        </div>
      </section>

      <section className="flex items-end justify-between gap-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bronze">Most Sold Books</p>
          <h2 className="mt-3 font-display text-5xl text-ink">What readers buy the most</h2>
        </div>
        <Link to="/books" className="btn-secondary">
          View Full Book List
        </Link>
      </section>

      <Alert message={error} />
      {loading ? <Loader text="Loading most sold books..." /> : null}

      <section className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        {topBooks.map((book) => (
          <BookCard
            key={book.id}
            book={book}
            onAddToWishlist={(bookId) => dispatch(addWishlist({ book_id: bookId }))}
            onAskAssistant={handleAskAssistant}
          />
        ))}
      </section>
    </div>
  );
}
