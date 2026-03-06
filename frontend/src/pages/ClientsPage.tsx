import { useState } from "react";
import { useClientList, useClientCreate } from "@/hooks/use-clients";
import { ApiError } from "@/lib/api";
import { AppShell } from "@/components/layout/AppShell";
import { PageLoader } from "@/components/PageLoader";
import { PageError } from "@/components/PageError";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { toast } from "sonner";
import { Plus } from "lucide-react";

export default function ClientsPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ name: "", rut: "", contact_email: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const { data, isLoading, isError, refetch } = useClientList();
  const createMut = useClientCreate();

  const items = data?.items || [];

  return (
    <AppShell>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Clientes</h1>
          <Button onClick={() => setCreateOpen(true)} className="gap-2">
            <Plus className="h-4 w-4" /> Nuevo cliente
          </Button>
        </div>

        {isLoading && <PageLoader />}
        {isError && <PageError onRetry={refetch} />}

        {!isLoading && !isError && (
          <div className="rounded-lg border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>RUT</TableHead>
                  <TableHead>Email</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3} className="text-center text-muted-foreground py-8">Sin clientes</TableCell>
                  </TableRow>
                )}
                {items.map((c: any) => (
                  <TableRow key={c.id}>
                    <TableCell className="font-medium">{c.name}</TableCell>
                    <TableCell className="font-mono text-sm">{c.rut || "-"}</TableCell>
                    <TableCell>{c.contact_email || "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Nuevo cliente</DialogTitle></DialogHeader>
          <div className="space-y-4">
            {[
              { key: "name", label: "Nombre" },
              { key: "rut", label: "RUT" },
              { key: "contact_email", label: "Email de contacto" },
            ].map(({ key, label }) => (
              <div key={key} className="space-y-2">
                <Label>{label}</Label>
                <Input
                  value={(form as any)[key]}
                  onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                />
                {errors[key] && <p className="text-xs text-destructive">{errors[key]}</p>}
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancelar</Button>
            <Button
              onClick={() =>
                createMut.mutate(form, {
                  onSuccess: () => {
                    toast.success("Cliente creado");
                    setCreateOpen(false);
                    setForm({ name: "", rut: "", contact_email: "" });
                  },
                  onError: (err) => {
                    if (err instanceof ApiError && err.status === 422 && err.errors) {
                      const mapped: Record<string, string> = {};
                      for (const [k, v] of Object.entries(err.errors)) mapped[k] = Array.isArray(v) ? v[0] : v;
                      setErrors(mapped);
                    }
                  },
                })
              }
              disabled={createMut.isPending}
            >
              Crear
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
