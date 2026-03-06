import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useIntakeList, useIntakeApprove, useIntakeReject, useIntakePaste } from "@/hooks/use-intake";
import { AppShell } from "@/components/layout/AppShell";
import { PageLoader } from "@/components/PageLoader";
import { PageError } from "@/components/PageError";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

export default function IntakePage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("STAGED_PENDING_VALIDATION");
  const [rejectId, setRejectId] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteText, setPasteText] = useState("");

  const { data, isLoading, isError, refetch } = useIntakeList(tab);
  const approveMut = useIntakeApprove();
  const rejectMut = useIntakeReject();
  const pasteMut = useIntakePaste();

  const items = data?.items || [];

  return (
    <AppShell>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Intake — Requerimientos</h1>
          <Button onClick={() => setPasteOpen(true)}>+ Nuevo requerimiento</Button>
        </div>

        <Tabs value={tab} onValueChange={setTab}>
          <TabsList>
            <TabsTrigger value="STAGED_PENDING_VALIDATION">Pendientes</TabsTrigger>
            <TabsTrigger value="EN_COTIZACION">En Cotización</TabsTrigger>
            <TabsTrigger value="REJECTED">Archivadas</TabsTrigger>
          </TabsList>

          <TabsContent value={tab} className="mt-4">
            {isLoading && <PageLoader />}
            {isError && <PageError onRetry={refetch} />}
            {!isLoading && !isError && (
              <div className="rounded-lg border bg-card">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Título</TableHead>
                      <TableHead>Fuente</TableHead>
                      <TableHead>Fecha</TableHead>
                      <TableHead>Ítems</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead className="text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {items.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                          Sin requerimientos
                        </TableCell>
                      </TableRow>
                    )}
                    {items.map((item: any) => (
                      <TableRow
                        key={item.id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => navigate(`/intake/${item.id}`)}
                      >
                        <TableCell className="font-medium">{item.title}</TableCell>
                        <TableCell>{item.source}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{item.created_at?.slice(0, 10)}</TableCell>
                        <TableCell>{item.item_count ?? "-"}</TableCell>
                        <TableCell><StatusBadge status={item.validation_status || item.status} /></TableCell>
                        <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                          {tab === "STAGED_PENDING_VALIDATION" && (
                            <div className="flex gap-2 justify-end">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  approveMut.mutate(item.id, {
                                    onSuccess: () => toast.success("Requerimiento aprobado"),
                                  });
                                }}
                              >
                                Aprobar
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                className="text-destructive"
                                onClick={() => setRejectId(item.id)}
                              >
                                Rechazar
                              </Button>
                            </div>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>

      <Dialog open={pasteOpen} onOpenChange={(o) => { setPasteOpen(o); if (!o) setPasteText(""); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nuevo requerimiento</DialogTitle>
          </DialogHeader>
          <Textarea
            placeholder="Pega aquí el texto del requerimiento (email, WhatsApp, etc.)..."
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            rows={6}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => { setPasteOpen(false); setPasteText(""); }}>Cancelar</Button>
            <Button
              disabled={!pasteText.trim() || pasteMut.isPending}
              onClick={() => {
                pasteMut.mutate({ text: pasteText, source: "manual" }, {
                  onSuccess: () => {
                    toast.success("Requerimiento creado");
                    setPasteOpen(false);
                    setPasteText("");
                  },
                });
              }}
            >
              Crear requerimiento
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!rejectId} onOpenChange={() => setRejectId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rechazar requerimiento</DialogTitle>
          </DialogHeader>
          <Textarea
            placeholder="Motivo del rechazo..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectId(null)}>Cancelar</Button>
            <Button
              variant="destructive"
              disabled={!reason.trim() || rejectMut.isPending}
              onClick={() => {
                if (rejectId) {
                  rejectMut.mutate({ id: rejectId, reason }, {
                    onSuccess: () => {
                      toast.success("Requerimiento rechazado");
                      setRejectId(null);
                      setReason("");
                    },
                  });
                }
              }}
            >
              Confirmar rechazo
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
