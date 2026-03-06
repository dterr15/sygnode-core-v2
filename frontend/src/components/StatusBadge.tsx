import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

const statusConfig: Record<string, { label: string; className: string }> = {
  STAGED_PENDING_VALIDATION: { label: "Pendiente", className: "bg-warning/15 text-warning border-warning/30" },
  APPROVED_GENERATED: { label: "Aprobado", className: "bg-success/15 text-success border-success/30" },
  REJECTED: { label: "Rechazado", className: "bg-destructive/15 text-destructive border-destructive/30" },
  EN_COTIZACION: { label: "En Cotización", className: "bg-info/15 text-info border-info/30" },
  OPEN: { label: "Abierto", className: "bg-info/15 text-info border-info/30" },
  FROZEN: { label: "Congelado", className: "bg-muted-foreground/15 text-muted-foreground border-muted-foreground/30" },
  DRAFT: { label: "Borrador", className: "bg-muted-foreground/15 text-muted-foreground border-muted-foreground/30" },
  SENT: { label: "Enviado", className: "bg-primary/15 text-primary border-primary/30" },
  RECEIVED: { label: "Recibido", className: "bg-success/15 text-success border-success/30" },
  CLOSED: { label: "Cerrado", className: "bg-muted-foreground/15 text-muted-foreground border-muted-foreground/30" },
  ACTIVE: { label: "Activo", className: "bg-success/15 text-success border-success/30" },
  INACTIVE: { label: "Inactivo", className: "bg-muted-foreground/15 text-muted-foreground border-muted-foreground/30" },
};

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status] || { label: status, className: "bg-muted text-muted-foreground" };
  return (
    <Badge variant="outline" className={cn("text-xs font-medium", config.className, className)}>
      {config.label}
    </Badge>
  );
}
