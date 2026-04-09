import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { fetchWishlist, removeWishlist } from "../features/wishlist/wishlistSlice";
import Alert from "../components/Alert";

export default function WishlistPage({ onOpenAssistant, onSelectBook }) {
  const dispatch = useDispatch();
  const { items, error } = useSelector((state) => state.wishlist);

  useEffect(() => {
    dispatch(fetchWishlist());
  }, [dispatch]);

  return (
    <div className="py-8">
      <div className="surface p-8">
        <h1 className="font-display text-5xl">Wishlist</h1>
        <div className="mt-6">
          <Alert message={error} />
        </div>
        {!items.length ? <p className="mt-6 text-sm text-ink/60">Your wishlist is empty.</p> : null}
        <div className="mt-8 grid gap-4">
          {items.map((item) => (
            <div key={item.id} className="flex flex-wrap items-center justify-between gap-4 rounded-3xl bg-mist p-5">
              <div>
                <h3 className="font-display text-3xl">{item.book.title}</h3>
                <p className="text-sm text-ink/60">{item.book.author}</p>
              </div>
              <div className="flex gap-3">
                <button
                  type="button"
                  className="btn-cart disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={Number(item.book.stock_quantity || 0) <= 0}
                  onClick={() => {
                    onSelectBook(item.book);
                    onOpenAssistant();
                  }}
                >
                  {Number(item.book.stock_quantity || 0) > 0 ? "Order with Assistant" : "Out of Stock"}
                </button>
                <button type="button" className="btn-secondary" onClick={() => dispatch(removeWishlist(item.book.id))}>
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
