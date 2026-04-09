import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { logout } from "../features/auth/authSlice";

export default function Navbar({ onOpenAssistant }) {
  const { user } = useSelector((state) => state.auth);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const location = useLocation();

  function handleLogout() {
    dispatch(logout());
    navigate("/login");
  }

  function handleOpenAssistant() {
    if (!user) {
      navigate("/login", { state: { from: location } });
      return;
    }
    onOpenAssistant();
  }

  return (
    <header className="sticky top-0 z-30 border-b border-black/5 bg-white/75 backdrop-blur">
      <div className="mx-auto flex w-[min(1180px,calc(100%-32px))] items-center justify-between gap-6 py-4">
        <Link to="/" className="flex items-center gap-3">
          <div>
            <strong className="block text-lg">Online Bookstore</strong>
          </div>
        </Link>

        <nav className="hidden items-center gap-5 text-sm font-medium md:flex">
          <NavLink to="/">Home</NavLink>
          <NavLink to="/books">Book List</NavLink>
          {user ? <NavLink to="/profile">Account</NavLink> : null}
          <NavLink to="/wishlist">Wishlist</NavLink>
          <NavLink to="/orders">Orders</NavLink>
          {user?.role === "admin" ? <NavLink to="/admin">Admin</NavLink> : null}
        </nav>

        <div className="flex items-center gap-3">
          <button type="button" className="btn-secondary px-4 py-2" onClick={handleOpenAssistant}>
            Open Assistant
          </button>
          {user ? (
            <>
              <Link
                to="/profile"
                className="hidden rounded-full border border-black/10 bg-white/80 px-4 py-2 text-sm font-semibold text-ink/80 transition hover:bg-white sm:inline-flex"
              >
                {user.name}
              </Link>
              <button type="button" className="btn-primary px-4 py-2" onClick={handleLogout}>
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="btn-secondary px-4 py-2">
                Login
              </Link>
              <Link to="/register" className="btn-primary px-4 py-2">
                Register
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
