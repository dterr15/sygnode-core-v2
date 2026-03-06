import { LogOut, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useCurrentUser } from "@/hooks/use-auth";
import { api } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

export function TopBar() {
  const { data: user } = useCurrentUser();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await api.post("/api/v2/auth/logout");
    } catch {
      // ignore
    }
    navigate("/login");
    toast.success("Sesión cerrada");
  };

  return (
    <header className="flex items-center justify-between h-14 px-6 border-b bg-card shrink-0">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-semibold text-foreground">
          {user?.organization?.name || user?.organization_name || "Sygnode Core Engine"}
        </h2>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <User className="h-4 w-4" />
          <span>{user?.user?.name || user?.name || "Usuario"}</span>
          {(user?.user?.role || user?.role) && (
            <span className="text-xs bg-muted px-2 py-0.5 rounded-md">{user?.user?.role || user?.role}</span>
          )}
        </div>
        <Button variant="ghost" size="icon" onClick={handleLogout} title="Cerrar sesión">
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
