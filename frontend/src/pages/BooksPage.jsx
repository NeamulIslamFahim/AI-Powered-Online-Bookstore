import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useLocation, useNavigate } from "react-router-dom";
import Alert from "../components/Alert";
import BookCard from "../components/BookCard";
import Loader from "../components/Loader";
import Pagination from "../components/Pagination";
import { fetchBooks, fetchCategories } from "../features/books/bookSlice";
import { addWishlist } from "../features/wishlist/wishlistSlice";

export default function BooksPage({ onOpenAssistant, onSelectBook }) {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const { books, categories, pagination, loading, error } = useSelector((state) => state.books);
  const { token } = useSelector((state) => state.auth);
  const [filters, setFilters] = useState({
    page: 1,
    limit: 8,
    search: "",
    category: "",
    sort: "newest",
  });

  useEffect(() => {
    dispatch(fetchBooks(filters));
  }, [dispatch, filters]);

  useEffect(() => {
    dispatch(fetchCategories());
  }, [dispatch]);

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
      <section className="surface grid gap-8 p-8 md:grid-cols-[1.1fr_0.9fr]">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-bronze">Book List</p>
          <h1 className="mt-4 font-display text-6xl leading-none text-ink">Browse the complete bookstore catalog.</h1>
          <p className="mt-6 max-w-2xl text-base leading-8 text-ink/70">
            Explore every title, filter by category, compare prices, and start the assistant-led ordering flow from any book.
          </p>
        </div>
        <div className="rounded-[28px] bg-gradient-to-br from-[#264738] to-[#11261d] p-8 text-white shadow-card">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">Catalog tools</p>
          <div className="mt-4 space-y-4 text-sm leading-7 text-white/80">
            <p>Search by title or author.</p>
            <p>Sort by newest release, price, or best-selling performance.</p>
            <p>Move from any book directly into the assistant ordering flow.</p>
          </div>
        </div>
      </section>

      <section className="surface p-6">
        <div className="grid gap-4 md:grid-cols-4">
          <input
            className="input"
            placeholder="Search title or author"
            value={filters.search}
            onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value, page: 1 }))}
          />
          <select
            className="input"
            value={filters.category}
            onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value, page: 1 }))}
          >
            <option value="">All categories</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
          <select
            className="input"
            value={filters.sort}
            onChange={(event) => setFilters((current) => ({ ...current, sort: event.target.value, page: 1 }))}
          >
            <option value="newest">Newest</option>
            <option value="best_selling">Best Selling</option>
            <option value="price_asc">Price: Low to High</option>
            <option value="price_desc">Price: High to Low</option>
          </select>
          <button type="button" className="btn-secondary" onClick={() => setFilters((current) => ({ ...current, page: 1 }))}>
            Apply Filters
          </button>
        </div>
      </section>

      <Alert message={error} />
      {loading ? <Loader text="Loading bookstore catalog..." /> : null}

      <section className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        {books.map((book) => (
          <BookCard
            key={book.id}
            book={book}
            onAddToWishlist={(bookId) => dispatch(addWishlist({ book_id: bookId }))}
            onAskAssistant={handleAskAssistant}
          />
        ))}
      </section>

      <Pagination
        page={pagination.page}
        totalPages={pagination.total_pages}
        onChange={(page) => setFilters((current) => ({ ...current, page }))}
      />
    </div>
  );
}
