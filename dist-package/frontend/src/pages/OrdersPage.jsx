import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { fetchMyOrders } from "../features/orders/orderSlice";
import Alert from "../components/Alert";
import Loader from "../components/Loader";

export default function OrdersPage() {
  const dispatch = useDispatch();
  const { orders, loading, error } = useSelector((state) => state.orders);

  useEffect(() => {
    dispatch(fetchMyOrders());
  }, [dispatch]);

  if (loading) return <Loader text="Loading orders..." />;

  return (
    <div className="py-8">
      <div className="surface p-8">
        <h1 className="font-display text-5xl">My Orders</h1>
        <div className="mt-6">
          <Alert message={error} />
        </div>
        {!orders.length ? <p className="mt-6 text-sm text-ink/60">You have not placed any orders yet.</p> : null}
        <div className="mt-8 space-y-4">
          {orders.map((order) => (
            <article key={order.id} className="rounded-3xl bg-mist p-5">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">Order #{order.id}</h3>
                <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase">{order.status}</span>
              </div>
              <p className="mt-2 text-sm text-ink/60">Total: ${order.total_amount}</p>
              <div className="mt-4 space-y-2">
                {order.items.map((item) => (
                  <div key={item.id} className="flex justify-between text-sm text-ink/70">
                    <span>{item.book.title}</span>
                    <span>
                      {item.quantity} x ${item.price_at_purchase}
                    </span>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}
