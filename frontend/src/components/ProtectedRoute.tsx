import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { authApi } from "@/api/auth";

interface Props {
  children: React.ReactNode;
}

export default function ProtectedRoute({ children }: Props) {
  const { user, setUser } = useAuthStore();
  const [checking, setChecking] = useState(!user);
  const navigate = useNavigate();

  useEffect(() => {
    if (user) return;
    authApi
      .me()
      .then((res) => setUser(res.data))
      .catch(() => navigate("/login", { replace: true }))
      .finally(() => setChecking(false));
  }, []);

  if (checking) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 size={32} className="animate-spin text-blue-500" />
      </div>
    );
  }

  return user ? <>{children}</> : <Navigate to="/login" replace />;
}
