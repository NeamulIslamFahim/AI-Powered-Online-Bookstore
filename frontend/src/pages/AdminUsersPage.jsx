import { useEffect, useState } from "react";
import { fetchAdminUsersRequest, updateAdminUserRoleRequest, deleteAdminUserRequest } from "../api/adminApi";
import Alert from "../components/Alert";
import Loader from "../components/Loader";
import { useSelector } from "react-redux";

export default function AdminUsersPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { user: currentUser } = useSelector((state) => state.auth);

  useEffect(() => {
    loadUsers();
  }, []);

  async function loadUsers() {
    try {
      setLoading(true);
      const res = await fetchAdminUsersRequest();
      setUsers(res.data);
    } catch (err) {
      setError("Failed to load users.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRoleChange(userId, newRole) {
    try {
      await updateAdminUserRoleRequest(userId, newRole);
      setUsers(users.map(u => u.id === userId ? { ...u, role: newRole } : u));
    } catch (err) {
      alert("Failed to update user role");
    }
  }

  async function handleDelete(userId) {
    if (!window.confirm("Are you sure you want to delete this user?")) return;
    try {
      await deleteAdminUserRequest(userId);
      setUsers(users.filter(u => u.id !== userId));
    } catch (err) {
      alert("Failed to delete user");
    }
  }

  if (loading) return <Loader text="Loading users..." />;

  return (
    <div className="space-y-8 py-8">
      <section className="surface p-8">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bronze">Admin Users</p>
            <h1 className="mt-3 font-display text-5xl">Manage Users</h1>
          </div>
        </div>

        <div className="mt-6">
          <Alert message={error} />
        </div>

        <div className="mt-8 space-y-4">
          {!users.length ? <p className="text-sm text-ink/60">No users found.</p> : null}
          {users.map((u) => (
            <div key={u.id} className="rounded-3xl bg-mist p-5">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h3 className="font-display text-3xl">{u.name}</h3>
                  <p className="text-sm text-ink/60">{u.email}</p>
                  <p className="text-xs text-ink/50 mt-1">Joined: {new Date(u.created_at).toLocaleDateString()}</p>
                </div>
                <div className="flex gap-3 items-center">
                  <select 
                    className="input max-w-48"
                    value={u.role}
                    onChange={(e) => handleRoleChange(u.id, e.target.value)}
                    disabled={u.id === currentUser?.id}
                  >
                    <option value="customer">Customer</option>
                    <option value="admin">Admin</option>
                  </select>
                  {u.id !== currentUser?.id && (
                    <button type="button" className="btn-primary" onClick={() => handleDelete(u.id)}>
                      Delete
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
