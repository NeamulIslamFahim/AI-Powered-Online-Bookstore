import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { checkout } from "../features/orders/orderSlice";
import Alert from "../components/Alert";
import { clearCart } from "../features/cart/cartSlice";

export default function CheckoutPage() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { cart } = useSelector((state) => state.cart);
  const { error, loading } = useSelector((state) => state.orders);

  async function handleCheckout() {
    const action = await dispatch(checkout());
    if (!action.error) {
      dispatch(clearCart());
      navigate("/orders");
    }
  }

  return (
    <div className="py-8">
      <div className="surface mx-auto max-w-3xl p-8">
        <h1 className="font-display text-5xl">Checkout</h1>
        <Alert message={error} />
        {!cart?.items?.length ? (
          <p className="mt-6 text-sm text-ink/60">Your cart is empty. Add a book before checking out.</p>
        ) : null}
        <div className="mt-6 space-y-3">
          {cart?.items?.map((item) => (
            <div key={item.book.id} className="flex items-center justify-between rounded-2xl bg-mist px-4 py-3">
              <span>{item.book.title}</span>
              <span>${item.subtotal}</span>
            </div>
          ))}
        </div>
        <div className="mt-8 flex items-center justify-between">
          <span className="text-xl font-bold">Total: ${cart?.subtotal || 0}</span>
          <button
            type="button"
            className="btn-primary disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!cart?.items?.length || loading}
            onClick={handleCheckout}
          >
            {loading ? "Processing..." : "Confirm Checkout"}
          </button>
        </div>
      </div>
    </div>
  );
}
