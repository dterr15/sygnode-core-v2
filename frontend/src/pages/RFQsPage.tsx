import { useNavigate } from "react-router-dom";
import { useRFQList } from "@/hooks/use-rfqs";
import { AppShell } from "@/components/layout/AppShell";
import { PageLoader } from "@/components/PageLoader";
import { PageError } from "@/components/PageError";
import { StatusBadge } from "@/components/StatusBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export default function RFQsPage() {
  const navigate = useNavigate();
  const { data, isLoading, isError, refetch } = useRFQList();

  const items = data?.items || [];

  return (
    <AppShell>
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">RFQs</h1>

        {isLoading && <PageLoader />}
        {isError && <PageError onRetry={refetch} />}

        {!isLoading && !isError && (
          <div className="rounded-lg border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Código</TableHead>
                  <TableHead>Título</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Fecha</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground py-8">Sin RFQs</TableCell>
                  </TableRow>
                )}
                {items.map((rfq: any) => (
                  <TableRow key={rfq.id} className="cursor-pointer hover:bg-muted/50" onClick={() => navigate(`/rfqs/${rfq.id}`)}>
                    <TableCell className="font-mono text-xs">{rfq.reference_code}</TableCell>
                    <TableCell className="font-medium">{rfq.title}</TableCell>
                    <TableCell><StatusBadge status={rfq.status} /></TableCell>
                    <TableCell className="text-sm text-muted-foreground">{rfq.created_at?.slice(0, 10)}</TableCell>
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
