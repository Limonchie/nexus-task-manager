import { useEffect } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { useAuthStore } from "../../stores/authStore";

export function DashboardLayout() {
  const navigate = useNavigate();
  const { user, fetchMe, logout, isAuthenticated } = useAuthStore();

  useEffect(() => {
    fetchMe().then((u) => {
      if (!u) navigate("/login", { replace: true });
    });
  }, [fetchMe, navigate]);

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  if (!user) return <div className="p-8">Loading...</div>;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b flex items-center justify-between px-6 py-4">
        <h1 className="text-xl font-semibold">Nexus Task Manager</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">{user.email}</span>
          <button
            onClick={handleLogout}
            className="text-sm text-blue-600 hover:underline"
          >
            Logout
          </button>
        </div>
      </header>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
