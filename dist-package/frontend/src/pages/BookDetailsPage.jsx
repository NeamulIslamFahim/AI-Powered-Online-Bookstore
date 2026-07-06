import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { fetchBookDetails } from "../features/books/bookSlice";
import { addWishlist } from "../features/wishlist/wishlistSlice";
import { createReviewRequest, fetchReviewsByBookRequest } from "../api/reviewsApi";
import { getApiError } from "../utils/apiError";
import Loader from "../components/Loader";
import RatingStars from "../components/RatingStars";
import Alert from "../components/Alert";

export default function BookDetailsPage({ onOpenAssistant, onSelectBook }) {
  const { id } = useParams();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const { selectedBook } = useSelector((state) => state.books);
  const { token } = useSelector((state) => state.auth);
  const [reviews, setReviews] = useState([]);
  const [reviewError, setReviewError] = useState(null);
  const [reviewsLoading, setReviewsLoading] = useState(true);
  const [form, setForm] = useState({ rating: 5, comment: "" });

  useEffect(() => {
    dispatch(fetchBookDetails(id));
    setReviewsLoading(true);
    fetchReviewsByBookRequest(id)
      .then((response) => {
        setReviews(response.data);
        setReviewError(null);
      })
      .catch((error) => {
        setReviewError(getApiError(error, "Unable to load reviews"));
      })
      .finally(() => setReviewsLoading(false));
  }, [dispatch, id]);

  async function handleReviewSubmit(event) {
    event.preventDefault();
    try {
      const response = await createReviewRequest({ ...form, book_id: Number(id) });
      setReviews((current) => [response.data, ...current]);
      setForm({ rating: 5, comment: "" });
      setReviewError(null);
    } catch (error) {
      setReviewError(getApiError(error, "Unable to submit review"));
    }
  }

  if (!selectedBook) return <Loader text="Loading book details..." />;
  const inStock = Number(selectedBook.stock_quantity || 0) > 0;

  function handleOrderWithAssistant() {
    if (!token) {
      navigate("/login", { state: { from: location } });
      return;
    }

    onSelectBook(selectedBook);
    onOpenAssistant();
  }

  return (
    <div className="space-y-8 py-8">
      <section className="surface grid gap-8 p-8 md:grid-cols-[0.7fr_1.3fr]">
        <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-amber-200 to-rose-200" style={{ minHeight: "340px" }}>
          {selectedBook.image_url ? (
            <img
              src={selectedBook.image_url}
              alt={`${selectedBook.title} cover`}
              className="h-full w-full object-cover"
              style={{ minHeight: "340px" }}
              onError={(e) => { e.currentTarget.style.display = "none"; }}
            />
          ) : (
            <div className="flex h-full min-h-[340px] items-center justify-center text-6xl opacity-30">📚</div>
          )}
        </div>

        <div className="space-y-5">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-bronze">
            {selectedBook.category?.name}
          </p>
          <h1 className="font-display text-6xl leading-none">{selectedBook.title}</h1>
          <p className="text-lg font-semibold text-ink/60">{selectedBook.author}</p>
          <RatingStars rating={selectedBook.average_rating || 0} />
          <p className="text-base leading-8 text-ink/70">{selectedBook.description}</p>
          <div className="flex flex-wrap gap-4 text-sm text-ink/60">
            <span>ISBN: {selectedBook.isbn}</span>
            <span>Published: {selectedBook.published_date}</span>
            <span>Stock: {selectedBook.stock_quantity}</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-3xl font-bold text-ember">${selectedBook.price}</span>
            <button
              type="button"
              className="btn-cart disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!inStock}
              onClick={handleOrderWithAssistant}
            >
              {inStock ? "Order with Assistant" : "Out of Stock"}
            </button>
            <button type="button" className="btn-secondary" onClick={() => dispatch(addWishlist({ book_id: selectedBook.id }))}>
              Add to Wishlist
            </button>
          </div>
        </div>
      </section>

      <section className="surface p-8">
        <h2 className="font-display text-4xl">Reviews</h2>
        <form className="mt-6 grid gap-4" onSubmit={handleReviewSubmit}>
          <Alert message={reviewError} />
          <select className="input max-w-40" value={form.rating} onChange={(e) => setForm((c) => ({ ...c, rating: Number(e.target.value) }))}>
            {[5, 4, 3, 2, 1].map((value) => (
              <option key={value} value={value}>
                {value} Stars
              </option>
            ))}
          </select>
          <textarea className="input min-h-28" value={form.comment} onChange={(e) => setForm((c) => ({ ...c, comment: e.target.value }))} />
          <button type="submit" className="btn-primary w-fit">
            Submit Review
          </button>
        </form>

        <div className="mt-8 space-y-4">
          {reviewsLoading ? <Loader text="Loading reviews..." /> : null}
          {!reviewsLoading && !reviews.length ? (
            <p className="text-sm text-ink/60">No reviews yet. Be the first to review this book.</p>
          ) : null}
          {reviews.map((review) => (
            <article key={review.id} className="rounded-3xl border border-black/5 bg-mist p-5">
              <div className="flex items-center justify-between">
                <strong>{review.user?.name || "Customer"}</strong>
                <RatingStars rating={review.rating} />
              </div>
              <p className="mt-3 text-sm leading-6 text-ink/70">{review.comment}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
