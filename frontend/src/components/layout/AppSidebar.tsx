import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard, Inbox, FileText, Scale, Building2, Users, ShieldCheck, Settings, ChevronLeft, ChevronRight,
} from "lucide-react";
import { useUIStore } from "@/stores/ui-store";
import { Button } from "@/components/ui/button";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/intake", icon: Inbox, label: "Intake" },
  { to: "/rfqs", icon: FileText, label: "RFQs" },
  { to: "/cases", icon: Scale, label: "Casos" },
  { to: "/suppliers", icon: Building2, label: "Proveedores" },
  { to: "/clients", icon: Users, label: "Clientes" },
  { to: "/validations", icon: ShieldCheck, label: "Validaciones" },
  { to: "/settings", icon: Settings, label: "Configuración" },
];

export function AppSidebar() {
  const location = useLocation();
  const { sidebarOpen, toggleSidebar } = useUIStore();

  return (
    <aside
      className={cn(
        "relative flex flex-col bg-sidebar text-sidebar-foreground border-r border-sidebar-border transition-all duration-300 shrink-0",
        sidebarOpen ? "w-60" : "w-16"
      )}
    >
      {/* Logo */}
      <div className="flex items-center h-14 px-4 border-b border-sidebar-border">
        {sidebarOpen && (
          <span className="text-lg font-bold text-sidebar-primary tracking-tight">Sygnode</span>
        )}
        {!sidebarOpen && (
          <span className="text-lg font-bold text-sidebar-primary mx-auto">S</span>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 space-y-0.5 px-2">
        {navItems.map((item) => {
          const isActive = item.to === "/" ? location.pathname === "/" : location.pathname.startsWith(item.to);
          return (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-primary"
                  : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {sidebarOpen && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Collapse toggle */}
      <Button
        variant="ghost"
        size="icon"
        onClick={toggleSidebar}
        className="absolute -right-3 top-16 z-10 h-6 w-6 rounded-full border bg-card text-muted-foreground shadow-sm hover:bg-muted"
      >
        {sidebarOpen ? <ChevronLeft className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
      </Button>
    </aside>
  );
}
