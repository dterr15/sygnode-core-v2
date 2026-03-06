import { useState } from "react";
import { useSupplierList, useSupplierCreate } from "@/hooks/use-suppliers";
import { ApiError } from "@/lib/api";
import { AppShell } from "@/components/layout/AppShell";
import { PageLoader } from "@/components/PageLoader";
import { PageError } from "@/components/PageError";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { toast } from "sonner";
import { Plus, CheckCircle, XCircle } from "lucide-react";

export default function SuppliersPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ name: "", rut: "", email: "", phone: "", city: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const { data, isLoading, isError, refetch } = useSupplierList();
  const createMut = useSupplierCreate();

  const items = data?.items || [];

  return (
    <AppShell>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Proveedores</h1>
          <Button onClick={() => setCreateOpen(true)} className="gap-2">
            <Plus className="h-4 w-4" /> Nuevo proveedor
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
                  <TableHead>Ciudad</TableHead>
                  <TableHead>Categorías</TableHead>
                  <TableHead>Confianza</TableHead>
                  <TableHead>Validado</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground py-8">Sin proveedores</TableCell>
                  </TableRow>
                )}
                {items.map((s: any) => (
                  <TableRow key={s.id}>
                    <TableCell className="font-medium">{s.name}</TableCell>
                    <TableCell className="font-mono text-sm">{s.rut || "-"}</TableCell>
                    <TableCell>{s.city || "-"}</TableCell>
                    <TableCell>
                      <div className="flex gap-1 flex-wrap">
                        {(s.categories || []).map((cat: string) => (
                          <Badge key={cat} variant="secondary" className="text-xs">{cat}</Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>{s.confidence_score != null ? `${s.confidence_score}%` : "-"}</TableCell>
                    <TableCell>
                      {s.is_validated ? (
                        <CheckCircle className="h-4 w-4 text-success" />
                      ) : (
                        <XCircle className="h-4 w-4 text-muted-foreground" />
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Nuevo proveedor</DialogTitle></DialogHeader>
          <div className="space-y-4">
            {[
              { key: "name", label: "Nombre", required: true },
              { key: "rut", label: "RUT", required: false },
              { key: "email", label: "Email", required: false },
              { key: "phone", label: "Teléfono", required: false },
              { key: "city", label: "Ciudad", required: false },
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
                    toast.success("Proveedor creado");
                    setCreateOpen(false);
                    setForm({ name: "", rut: "", email: "", phone: "", city: "" });
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
