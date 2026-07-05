import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import { clearCart, fetchCart, removeCartItem, updateCartItem } from "../features/cart/cartSlice";
import Alert from "../components/Alert";
import Loader from "../components/Loader";

export default function CartPage() {
  const dispatch = useDispatch();
  const { cart, loading, error } = useSelector((state) => state.cart);

  useEffect(() => {
    dispatch(fetchCart());
  }, [dispatch]);

  if (loading) return <Loader text="Loading cart..." />;

  return (
    <div className="space-y-8 py-8">
      <div className="surface p-8">
        <div className="flex items-center justify-between">
          <h1 className="font-display text-5xl">Your Cart</h1>
          <button type="button" className="btn-secondary" onClick={() => dispatch(clearCart())}>
            Clear Cart
          </button>
        </div>
        <div className="mt-6">
          <Alert message={error} />
        </div>
        <div className="mt-8 space-y-4">
          {cart?.items?.map((item) => (
            <div key={item.book.id} className="flex flex-wrap items-center justify-between gap-4 rounded-3xl bg-mist p-5">
              <div>
                <h3 className="font-display text-3xl">{item.book.title}</h3>
                <p className="text-sm text-ink/60">{item.book.author}</p>
              </div>
              <div className="flex items-center gap-3">
                <input
                  className="input w-24"
                  type="number"
                  value={item.quantity}
                  min="1"
                  onChange={(e) =>
                    dispatch(updateCartItem({ book_id: item.book.id, quantity: Number(e.target.value) }))
                  }
                />
                <span className="font-bold text-ember">${item.subtotal}</span>
                <button type="button" className="btn-secondary" onClick={() => dispatch(removeCartItem(item.book.id))}>
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-8 flex items-center justify-between border-t border-black/10 pt-6">
          <p className="text-lg font-semibold">Subtotal: ${cart?.subtotal || 0}</p>
          <Link to="/checkout" className="btn-primary">
            Proceed to Checkout
          </Link>
        </div>
      </div>
    </div>
  );
}
