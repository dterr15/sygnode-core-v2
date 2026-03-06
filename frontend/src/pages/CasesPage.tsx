import { useNavigate } from "react-router-dom";
import { formatDate } from "@/lib/utils";
import { useCaseList } from "@/hooks/use-cases";
import { AppShell } from "@/components/layout/AppShell";
import { PageLoader } from "@/components/PageLoader";
import { PageError } from "@/components/PageError";
import { StatusBadge } from "@/components/StatusBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

export default function CasesPage() {
  const navigate = useNavigate();
  const { data, isLoading, isError, refetch } = useCaseList();

  const items = data?.items || [];

  return (
    <AppShell>
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Casos de Decisión</h1>

        {isLoading && <PageLoader />}
        {isError && <PageError onRetry={refetch} />}

        {!isLoading && !isError && (
          <div className="rounded-lg border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Referencia</TableHead>
                  <TableHead>Criticidad</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Evidencias</TableHead>
                  <TableHead>Gaps</TableHead>
                  <TableHead>OC</TableHead>
                  <TableHead>Fecha</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-8">Sin casos</TableCell>
                  </TableRow>
                )}
                {items.map((c: any) => (
                  <TableRow key={c.id} className="cursor-pointer hover:bg-muted/50" onClick={() => navigate(`/cases/${c.id}`)}>
                    <TableCell className="font-mono text-xs">{c.case_reference}</TableCell>
                    <TableCell><StatusBadge status={c.criticality} /></TableCell>
                    <TableCell><StatusBadge status={c.status} /></TableCell>
                    <TableCell>{c.evidence_count}</TableCell>
                    <TableCell>{c.gap_count}</TableCell>
                    <TableCell>
                      {c.has_fulfillment ? (
                        <Badge variant="outline" className="text-xs">Sí</Badge>
                      ) : (
                        <span className="text-muted-foreground text-xs">No</span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{formatDate(c.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </AppShell>
  );
}
