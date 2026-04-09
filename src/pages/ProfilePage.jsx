import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useSelector } from "react-redux";
import { formatPrice } from "../utils/formatters";

export default function ProfilePage() {
  const { user } = useSelector((state) => state.auth);
  const { cart } = useSelector((state) => state.cart);
  const { items: wishlistItems } = useSelector((state) => state.wishlist);
  const { orders } = useSelector((state) => state.orders);

  const joinedDate = useMemo(() => {
    if (!user?.created_at) return "Recently";
    return new Date(user.created_at).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }, [user]);

  const latestOrder = orders?.[0] || null;

  return (
    <div className="space-y-8 py-8">
      <section className="surface grid gap-8 p-8 md:grid-cols-[1.1fr_0.9fr]">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-bronze">My Account</p>
          <h1 className="mt-4 font-display text-6xl leading-none text-ink">
            {user?.name || "Bookstore Reader"}
          </h1>
          <p className="mt-5 text-base leading-8 text-ink/70">
            Manage your profile, keep track of your orders, and jump back into your saved books and cart.
          </p>

          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            <div className="rounded-3xl bg-mist p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bronze">Email</p>
              <p className="mt-3 text-lg font-semibold text-ink">{user?.email || "-"}</p>
            </div>
            <div className="rounded-3xl bg-mist p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bronze">Joined</p>
              <p className="mt-3 text-lg font-semibold text-ink">{joinedDate}</p>
            </div>
            <div className="rounded-3xl bg-mist p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bronze">Role</p>
              <p className="mt-3 text-lg font-semibold capitalize text-ink">{user?.role || "customer"}</p>
            </div>
            <div className="rounded-3xl bg-mist p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bronze">Current Cart</p>
              <p className="mt-3 text-lg font-semibold text-ink">
                {cart?.items?.length || 0} item{cart?.items?.length === 1 ? "" : "s"}
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-[28px] bg-gradient-to-br from-[#5f2d18] to-[#24140c] p-8 text-white shadow-card">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">Account Snapshot</p>
          <div className="mt-6 space-y-5">
            <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
              <p className="text-sm text-white/70">Wishlist</p>
              <p className="mt-2 font-display text-5xl">{wishlistItems?.length || 0}</p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
              <p className="text-sm text-white/70">Orders</p>
              <p className="mt-2 font-display text-5xl">{orders?.length || 0}</p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
              <p className="text-sm text-white/70">Latest Order</p>
              <p className="mt-2 text-lg font-semibold">
                {latestOrder ? `#${latestOrder.id} • ${formatPrice(latestOrder.total_amount)}` : "No orders yet"}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-3">
        <Link to="/orders" className="surface p-6 transition hover:-translate-y-0.5">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bronze">Orders</p>
          <h2 className="mt-3 font-display text-4xl">View order history</h2>
          <p className="mt-4 text-sm leading-7 text-ink/65">Track your purchases and see the latest status updates.</p>
        </Link>

        <Link to="/wishlist" className="surface p-6 transition hover:-translate-y-0.5">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bronze">Wishlist</p>
          <h2 className="mt-3 font-display text-4xl">Saved books</h2>
          <p className="mt-4 text-sm leading-7 text-ink/65">Return to the titles you bookmarked for later.</p>
        </Link>

        <Link to="/cart" className="surface p-6 transition hover:-translate-y-0.5">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bronze">Cart</p>
          <h2 className="mt-3 font-display text-4xl">Continue checkout</h2>
          <p className="mt-4 text-sm leading-7 text-ink/65">Pick up where you left off and place your next order.</p>
        </Link>
      </section>
    </div>
  );
}
