import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AppShell } from "@/components/layout/AppShell";
import { PageLoader } from "@/components/PageLoader";
import { PageError } from "@/components/PageError";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { Check, X } from "lucide-react";

export default function ValidationsPage() {
  const queryClient = useQueryClient();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["validations"],
    queryFn: () => api.get("/api/v2/validations"),
  });

  const approveMut = useMutation({
    mutationFn: (id: string) => api.post(`/api/v2/validations/${id}/approve`),
    onSuccess: () => {
      toast.success("Validación aprobada");
      queryClient.invalidateQueries({ queryKey: ["validations"] });
    },
  });

  const rejectMut = useMutation({
    mutationFn: (id: string) => api.post(`/api/v2/validations/${id}/reject`),
    onSuccess: () => {
      toast.success("Validación rechazada");
      queryClient.invalidateQueries({ queryKey: ["validations"] });
    },
  });

  const items = Array.isArray(data) ? data : data?.items || [];

  return (
    <AppShell>
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Validaciones ML Pendientes</h1>

        {isLoading && <PageLoader />}
        {isError && <PageError onRetry={refetch} />}

        {!isLoading && !isError && (
          <div className="rounded-lg border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Descripción</TableHead>
                  <TableHead>Confianza</TableHead>
                  <TableHead>Fuente</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-muted-foreground py-8">Sin validaciones pendientes</TableCell>
                  </TableRow>
                )}
                {items.map((v: any) => (
                  <TableRow key={v.id}>
                    <TableCell className="font-medium">{v.type}</TableCell>
                    <TableCell>{v.description}</TableCell>
                    <TableCell>{v.confidence ? `${(v.confidence * 100).toFixed(0)}%` : "-"}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{v.source}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button size="icon" variant="ghost" onClick={() => approveMut.mutate(v.id)} title="Aprobar">
                          <Check className="h-4 w-4 text-success" />
                        </Button>
                        <Button size="icon" variant="ghost" onClick={() => rejectMut.mutate(v.id)} title="Rechazar">
                          <X className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
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
