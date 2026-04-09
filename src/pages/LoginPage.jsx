import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useLocation, useNavigate } from "react-router-dom";
import Alert from "../components/Alert";
import { fetchCurrentUser, loginUser } from "../features/auth/authSlice";

export default function LoginPage() {
  const [form, setForm] = useState({ email: "", password: "" });
  const { token, user, loading, error } = useSelector((state) => state.auth);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (token && !user) {
      dispatch(fetchCurrentUser());
    }
  }, [dispatch, token, user]);

  useEffect(() => {
    if (user) {
      navigate(location.state?.from?.pathname || "/");
    }
  }, [navigate, location, user]);

  function handleSubmit(event) {
    event.preventDefault();
    dispatch(
      loginUser({
        email: form.email.trim(),
        password: form.password,
      })
    );
  }

  return (
    <div className="mx-auto max-w-xl py-10">
      <div className="surface p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-bronze">Welcome back</p>
        <h1 className="mt-4 font-display text-5xl">Login to your bookstore account</h1>
        <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
          <Alert message={error} />
          <input className="input" type="email" placeholder="Email" required value={form.email} onChange={(e) => setForm((c) => ({ ...c, email: e.target.value }))} />
          <input className="input" type="password" placeholder="Password" required value={form.password} onChange={(e) => setForm((c) => ({ ...c, password: e.target.value }))} />
          <button type="submit" className="btn-primary w-full">
            {loading ? "Signing in..." : "Login"}
          </button>
        </form>
        <p className="mt-6 text-sm text-ink/60">
          Need an account?{" "}
          <Link to="/register" className="font-semibold text-ember">
            Register here
          </Link>
        </p>
      </div>
    </div>
  );
}
