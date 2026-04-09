import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import Alert from "../components/Alert";
import { registerUser } from "../features/auth/authSlice";

export default function RegisterPage() {
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const { loading, error } = useSelector((state) => state.auth);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  async function handleSubmit(event) {
    event.preventDefault();
    const payload = {
      name: form.name.trim(),
      email: form.email.trim(),
      password: form.password,
    };
    const action = await dispatch(registerUser(payload));
    if (!action.error) navigate("/login");
  }

  return (
    <div className="mx-auto max-w-xl py-10">
      <div className="surface p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-bronze">Create account</p>
        <h1 className="mt-4 font-display text-5xl">Join the bookstore</h1>
        <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
          <Alert message={error} />
          <input className="input" placeholder="Full name" required minLength={2} value={form.name} onChange={(e) => setForm((c) => ({ ...c, name: e.target.value }))} />
          <input className="input" type="email" placeholder="Email" required value={form.email} onChange={(e) => setForm((c) => ({ ...c, email: e.target.value }))} />
          <input className="input" type="password" placeholder="Password" required minLength={6} value={form.password} onChange={(e) => setForm((c) => ({ ...c, password: e.target.value }))} />
          <button type="submit" className="btn-primary w-full">
            {loading ? "Creating account..." : "Register"}
          </button>
        </form>
        <p className="mt-6 text-sm text-ink/60">
          Already registered?{" "}
          <Link to="/login" className="font-semibold text-ember">
            Login
          </Link>
        </p>
      </div>
    </div>
  );
}
