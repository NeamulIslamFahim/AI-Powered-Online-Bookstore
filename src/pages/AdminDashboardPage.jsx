import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { fetchAdminOrders, fetchAdminStats, updateOrderStatus } from "../features/orders/orderSlice";
import Alert from "../components/Alert";
import Loader from "../components/Loader";
import { formatPrice } from "../utils/formatters";

function MetricCard({ label, value, hint }) {
  return (
    <div className="surface p-5">
      <p className="text-sm text-ink/50">{label}</p>
      <p className="mt-3 font-display text-5xl text-ink">{value}</p>
      {hint ? <p className="mt-2 text-xs uppercase tracking-[0.18em] text-bronze">{hint}</p> : null}
    </div>
  );
}

export default function AdminDashboardPage() {
  const dispatch = useDispatch();
  const { stats, adminOrders, loading, error } = useSelector((state) => state.orders);
  const defaultRange = useMemo(() => {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 6);
    return {
      startDate: start.toISOString().slice(0, 10),
      endDate: end.toISOString().slice(0, 10),
    };
  }, []);
  const [range, setRange] = useState(defaultRange);
  const timeline = stats?.sales_timeline || [];

  useEffect(() => {
    dispatch(fetchAdminOrders());
  }, [dispatch]);

  useEffect(() => {
    dispatch(fetchAdminStats({ start_date: range.startDate, end_date: range.endDate }));
  }, [dispatch, range.endDate, range.startDate]);

  if (loading && !stats) {
    return <Loader text="Loading admin dashboard..." />;
  }

  return (
    <div className="space-y-8 py-8">
      <section className="surface grid gap-8 p-8 md:grid-cols-[1.1fr_0.9fr]">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-bronze">Admin Control Center</p>
          <h1 className="mt-4 font-display text-6xl leading-none text-ink">Business clarity for bookstore operations.</h1>
          <p className="mt-6 max-w-2xl text-base leading-8 text-ink/70">
            Track revenue, best-sellers, pricing, inventory health, and order movement from one admin-only workspace.
          </p>
        </div>
        <div className="rounded-[28px] bg-gradient-to-br from-[#182f26] to-[#0d1713] p-8 text-white shadow-card">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">Admin Access</p>
          <div className="mt-4 space-y-4 text-sm leading-7 text-white/80">
            <p>The dashboard is visible only to users with the admin role.</p>
            <p>Use the separate admin email and password to enter this panel.</p>
            <p>Manage books, inspect sales, and monitor business performance with one account.</p>
          </div>
          <div className="mt-6">
            <Link to="/admin/books" className="btn-secondary">
              Manage Book Catalog
            </Link>
          </div>
        </div>
      </section>

      <Alert message={error} />

      <section className="grid gap-5 md:grid-cols-3 xl:grid-cols-6">
        <MetricCard label="Total Revenue" value={formatPrice(stats?.total_revenue || 0)} hint="lifetime" />
        <MetricCard label="Orders" value={stats?.total_orders || 0} hint={`${stats?.pending_orders || 0} pending`} />
        <MetricCard label="Units Sold" value={stats?.total_units_sold || 0} hint="books sold" />
        <MetricCard label="Average Order" value={formatPrice(stats?.average_order_value || 0)} hint="order value" />
        <MetricCard label="Users" value={stats?.total_users || 0} hint="registered" />
        <MetricCard label="Books" value={stats?.total_books || 0} hint={`${stats?.low_stock_books?.length || 0} low stock`} />
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="surface p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bronze">Sales Windows</p>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            <div className="rounded-3xl bg-mist p-5">
              <p className="text-sm text-ink/50">Today</p>
              <p className="mt-2 font-display text-4xl">{formatPrice(stats?.revenue_today || 0)}</p>
              <p className="mt-2 text-sm text-ink/60">{stats?.orders_today || 0} orders</p>
            </div>
            <div className="rounded-3xl bg-mist p-5">
              <p className="text-sm text-ink/50">This Month</p>
              <p className="mt-2 font-display text-4xl">{formatPrice(stats?.revenue_month || 0)}</p>
              <p className="mt-2 text-sm text-ink/60">{stats?.orders_month || 0} orders</p>
            </div>
            <div className="rounded-3xl bg-mist p-5">
              <p className="text-sm text-ink/50">This Year</p>
              <p className="mt-2 font-display text-4xl">{formatPrice(stats?.revenue_year || 0)}</p>
              <p className="mt-2 text-sm text-ink/60">{stats?.orders_year || 0} orders</p>
            </div>
          </div>

          <div className="mt-8">
            {!!timeline.length ? (
              <div className="mt-4 rounded-[28px] border border-black/5 bg-[#fbf6ef] p-5 md:p-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.18em] text-bronze">Editable Range</p>
                    <p className="mt-2 text-sm text-ink/60">
                      Showing timeline from {stats?.range_start || range.startDate} to {stats?.range_end || range.endDate}
                    </p>
                    <p className="mt-2 text-sm text-ink/60">Daily results are listed below in a clean business summary format.</p>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="block">
                      <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.14em] text-ink/50">Start Date</span>
                      <input
                        type="date"
                        className="input min-w-40 bg-white"
                        value={range.startDate}
                        max={range.endDate}
                        onChange={(event) =>
                          setRange((current) => ({
                            ...current,
                            startDate: event.target.value,
                          }))
                        }
                      />
                    </label>
                    <label className="block">
                      <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.14em] text-ink/50">End Date</span>
                      <input
                        type="date"
                        className="input min-w-40 bg-white"
                        value={range.endDate}
                        min={range.startDate}
                        onChange={(event) =>
                          setRange((current) => ({
                            ...current,
                            endDate: event.target.value,
                          }))
                        }
                      />
                    </label>
                  </div>
                </div>

                <div className="mt-5 grid gap-3 sm:grid-cols-3">
                  <div className="rounded-2xl bg-white/85 px-4 py-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink/50">Days Selected</p>
                    <p className="mt-2 text-xl font-bold text-ink">{timeline.length}</p>
                  </div>
                  <div className="rounded-2xl bg-white/85 px-4 py-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink/50">Range Revenue</p>
                    <p className="mt-2 text-xl font-bold text-ink">
                      {formatPrice(timeline.reduce((sum, point) => sum + Number(point.revenue || 0), 0))}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-white/85 px-4 py-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink/50">Range Orders</p>
                    <p className="mt-2 text-xl font-bold text-ink">
                      {timeline.reduce((sum, point) => sum + Number(point.orders || 0), 0)}
                    </p>
                  </div>
                </div>

                <div className="mt-5 overflow-hidden rounded-[24px] border border-black/5 bg-white/70">
                  <div className="grid grid-cols-[1.1fr_1fr_0.8fr_0.8fr] gap-4 border-b border-black/5 px-5 py-4 text-[11px] font-semibold uppercase tracking-[0.14em] text-ink/50">
                    <span>Date</span>
                    <span>Revenue</span>
                    <span>Orders</span>
                    <span>Units Sold</span>
                  </div>
                  <div className="max-h-[320px] overflow-y-auto">
                    {timeline.map((point, index) => (
                      <div
                        key={`${point.label}-${index}`}
                        className="grid grid-cols-[1.1fr_1fr_0.8fr_0.8fr] gap-4 border-b border-black/5 px-5 py-4 text-sm text-ink last:border-b-0"
                      >
                        <span className="font-semibold">{point.label}</span>
                        <span>{formatPrice(point.revenue)}</span>
                        <span>{point.orders}</span>
                        <span>{point.units_sold}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}
            {!timeline.length ? (
              <p className="mt-4 text-sm text-ink/60">No sales data found for this date range.</p>
            ) : null}
          </div>
        </div>

        <div className="surface p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bronze">Pricing and Inventory</p>
          <div className="mt-6 space-y-4">
            <div className="rounded-3xl bg-mist p-5">
              <p className="text-sm text-ink/50">Average Book Price</p>
              <p className="mt-2 font-display text-4xl">{formatPrice(stats?.pricing_overview?.average_price || 0)}</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-3xl bg-mist p-5">
                <p className="text-sm text-ink/50">Lowest Price</p>
                <p className="mt-2 text-2xl font-bold">{formatPrice(stats?.pricing_overview?.min_price || 0)}</p>
              </div>
              <div className="rounded-3xl bg-mist p-5">
                <p className="text-sm text-ink/50">Highest Price</p>
                <p className="mt-2 text-2xl font-bold">{formatPrice(stats?.pricing_overview?.max_price || 0)}</p>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-3xl bg-mist p-5">
                <p className="text-sm text-ink/50">Inventory Units</p>
                <p className="mt-2 text-2xl font-bold">{stats?.pricing_overview?.inventory_units || 0}</p>
              </div>
              <div className="rounded-3xl bg-mist p-5">
                <p className="text-sm text-ink/50">Retail Inventory Value</p>
                <p className="mt-2 text-2xl font-bold">{formatPrice(stats?.pricing_overview?.inventory_retail_value || 0)}</p>
              </div>
            </div>
            <div className="rounded-3xl border border-amber-200 bg-amber-50 p-5">
              <p className="text-sm font-semibold text-amber-900">Cancelled Orders</p>
              <p className="mt-2 text-2xl font-bold text-amber-900">{stats?.cancelled_orders || 0}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <div className="surface p-8">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bronze">Top Sold Books</p>
              <h2 className="mt-2 font-display text-4xl">Best business performers</h2>
            </div>
          </div>
          <div className="mt-8 space-y-4">
            {(stats?.top_selling_books || []).map((book) => (
              <div key={book.book_id} className="rounded-3xl bg-mist p-5">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <h3 className="font-display text-3xl">{book.title}</h3>
                    <p className="text-sm text-ink/60">{book.author}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-ink/50">{book.units_sold} sold</p>
                    <p className="text-lg font-bold text-ember">{formatPrice(book.revenue)}</p>
                    <p className="text-xs text-ink/60">{book.stock_quantity} left in stock</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="surface p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bronze">Category Performance</p>
          <h2 className="mt-2 font-display text-4xl">What categories drive the business</h2>
          <div className="mt-8 space-y-4">
            {(stats?.category_performance || []).map((category) => (
              <div key={category.category_name} className="rounded-3xl bg-mist p-5">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <h3 className="text-xl font-semibold">{category.category_name}</h3>
                    <p className="text-sm text-ink/60">{category.books_count} books in catalog</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-ink/50">{category.units_sold} units sold</p>
                    <p className="text-lg font-bold text-ember">{formatPrice(category.revenue)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
        <div className="surface p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bronze">Low Stock Watch</p>
          <h2 className="mt-2 font-display text-4xl">Books needing attention</h2>
          <div className="mt-8 space-y-4">
            {!(stats?.low_stock_books || []).length ? <p className="text-sm text-ink/60">No low-stock books right now.</p> : null}
            {(stats?.low_stock_books || []).map((book) => (
              <div key={book.id} className="rounded-3xl border border-red-100 bg-red-50 p-5">
                <p className="font-semibold text-red-900">{book.title}</p>
                <p className="mt-1 text-sm text-red-800">{book.author}</p>
                <p className="mt-2 text-sm font-semibold text-red-900">{book.stock_quantity} copies remaining</p>
              </div>
            ))}
          </div>
        </div>

        <div className="surface p-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bronze">Order Operations</p>
              <h2 className="mt-2 font-display text-4xl">Live order management</h2>
            </div>
            <Link to="/admin/books" className="btn-secondary">
              Add or Update Books
            </Link>
          </div>

          {!adminOrders.length ? <p className="mt-6 text-sm text-ink/60">No orders yet.</p> : null}
          <div className="mt-8 space-y-4">
            {adminOrders.map((order) => (
              <div key={order.id} className="rounded-3xl bg-mist p-5">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <h3 className="font-semibold">Order #{order.id}</h3>
                    <p className="text-sm text-ink/60">{order.user?.name} · {order.user?.email}</p>
                    <p className="mt-1 text-sm text-ink/60">{formatPrice(order.total_amount)} · {order.items.length} line items</p>
                  </div>
                  <select
                    className="input max-w-48"
                    value={order.status}
                    onChange={(e) => dispatch(updateOrderStatus({ id: order.id, status: e.target.value }))}
                  >
                    {["pending", "paid", "shipped", "delivered", "cancelled"].map((status) => (
                      <option key={status} value={status}>
                        {status}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
