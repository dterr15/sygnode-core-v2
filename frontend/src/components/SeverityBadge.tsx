import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

const severityConfig: Record<string, { label: string; className: string }> = {
  info: { label: "Info", className: "bg-info/15 text-info border-info/30" },
  warning: { label: "Advertencia", className: "bg-warning/15 text-warning border-warning/30" },
  critical: { label: "Crítico", className: "bg-destructive/15 text-destructive border-destructive/30" },
};

export function SeverityBadge({ severity, className }: { severity: string; className?: string }) {
  const config = severityConfig[severity] || severityConfig.info;
  return (
    <Badge variant="outline" className={cn("text-xs font-medium", config.className, className)}>
      {config.label}
    </Badge>
  );
}
