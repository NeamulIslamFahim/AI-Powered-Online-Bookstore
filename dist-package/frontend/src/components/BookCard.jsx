import { Link } from "react-router-dom";
import RatingStars from "./RatingStars";

export default function BookCard({ book, onAddToWishlist, onAskAssistant }) {
  const inStock = Number(book.stock_quantity || 0) > 0;

  return (
    <article className="surface overflow-hidden">
      <div className="relative h-48 overflow-hidden bg-gradient-to-br from-amber-200 via-orange-200 to-rose-200">
        {book.image_url ? (
          <img
            src={book.image_url}
            alt={`${book.title} cover`}
            className="h-full w-full object-cover"
            onError={(e) => { e.currentTarget.style.display = "none"; }}
          />
        ) : null}
        <div className="absolute top-3 left-3 rounded-full bg-white/80 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-bronze">
          {book.category?.name || "Book"}
        </div>
      </div>
      <div className="space-y-4 p-5">
        <div>
          <p className="text-sm font-semibold text-ink/50">{book.author}</p>
          <Link to={`/books/${book.id}`} className="mt-1 block font-display text-3xl leading-none text-ink hover:text-ember">
            {book.title}
          </Link>
        </div>
        <p className="line-clamp-3 text-sm leading-6 text-ink/70">{book.description}</p>
        <div className="flex items-center justify-between">
          <RatingStars rating={book.average_rating || 0} />
          <span className="text-xl font-bold text-ember">${book.price}</span>
        </div>
        <p className={`text-sm font-medium ${inStock ? "text-emerald-700" : "text-red-600"}`}>
          {inStock ? `${book.stock_quantity} copies available` : "Out of stock"}
        </p>
        <button
          type="button"
          className="btn-cart w-full justify-center disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!inStock}
          onClick={() => onAskAssistant(book)}
        >
          {inStock ? "Order with Assistant" : "Unavailable"}
        </button>
        <div className="grid grid-cols-2 gap-3">
          <Link to={`/books/${book.id}`} className="btn-secondary w-full justify-center text-sm">
            View Details
          </Link>
          <button type="button" className="btn-secondary w-full justify-center text-sm" onClick={() => onAddToWishlist(book.id)}>
            Wishlist
          </button>
        </div>
      </div>
    </article>
  );
}
