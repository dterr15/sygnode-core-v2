import { useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useRFQDetail, useRFQAnalyze, useRFQSendEmails, useRFQAddSupplier, useRFQItemSetSuppliers, useQuoteUpload, useQuoteProcess } from "@/hooks/use-rfqs";
import { useSupplierList } from "@/hooks/use-suppliers";
import { AppShell } from "@/components/layout/AppShell";
import { PageLoader } from "@/components/PageLoader";
import { PageError } from "@/components/PageError";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { ArrowLeft, Upload, Brain, Mail } from "lucide-react";
import { formatCLP } from "@/lib/utils";

export default function RFQDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [selectedSupplier, setSelectedSupplier] = useState("");
  const [selectedSupplierId, setSelectedSupplierId] = useState("");
  const [extractedItems, setExtractedItems] = useState<any[] | null>(null);

  const { data, isLoading, isError, refetch } = useRFQDetail(id);
  const suppliers = useSupplierList();
  const uploadMut = useQuoteUpload();
  const processMut = useQuoteProcess();
  const analyzeMut = useRFQAnalyze(id);
  const emailMut = useRFQSendEmails(id);
  const addSupplierMut = useRFQAddSupplier(id);
  const setSuppliersMut = useRFQItemSetSuppliers(id);

  // Backend returns { rfq, items, quotes, email_status }
  const rfq = data?.rfq;
  const rfqItems = data?.items || [];
  const quotes = data?.quotes || [];
  const analysisData = rfq?.analysis_data;
  const analysisMatrix = analysisData?.matrix;
  const recommendation = analysisData?.recommendation;
  const supplierList = suppliers.data?.items || [];

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file || !id) return;
    uploadMut.mutate(
      { file, rfq_id: id, supplier_id: selectedSupplier },
      {
        onSuccess: (doc) => {
          setUploadOpen(false);
          processMut.mutate(doc.id, {
            onSuccess: (result) => {
              setExtractedItems(result.items || []);
              toast.success("Cotización procesada");
              refetch();
            },
          });
        },
      }
    );
  };

  return (
    <AppShell>
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={() => navigate("/rfqs")} className="gap-1">
          <ArrowLeft className="h-4 w-4" /> Volver
        </Button>

        {isLoading && <PageLoader />}
        {isError && <PageError onRetry={refetch} />}

        {rfq && (
          <>
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-mono text-muted-foreground">{rfq.reference_code}</p>
                    <CardTitle className="text-xl">{rfq.title}</CardTitle>
                    {rfq.description && <p className="text-sm text-muted-foreground mt-1">{rfq.description}</p>}
                  </div>
                  <StatusBadge status={rfq.status} />
                </div>
              </CardHeader>
            </Card>

            <Tabs defaultValue="items">
              <TabsList>
                <TabsTrigger value="items">Ítems</TabsTrigger>
                <TabsTrigger value="quotes">Cotizaciones</TabsTrigger>
                <TabsTrigger value="analysis">Análisis</TabsTrigger>
                <TabsTrigger value="suppliers">Proveedores</TabsTrigger>
                <TabsTrigger value="emails">Emails</TabsTrigger>
              </TabsList>

              <TabsContent value="items" className="mt-4">
                <div className="rounded-lg border bg-card">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Descripción</TableHead>
                        <TableHead>Cantidad</TableHead>
                        <TableHead>Unidad</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {rfqItems.map((item: any) => (
                        <TableRow key={item.id}>
                          <TableCell>{item.description}</TableCell>
                          <TableCell>{item.quantity}</TableCell>
                          <TableCell>{item.unit}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </TabsContent>

              <TabsContent value="quotes" className="mt-4 space-y-4">
                <Button onClick={() => setUploadOpen(true)} className="gap-2">
                  <Upload className="h-4 w-4" /> Subir cotización
                </Button>
                <div className="rounded-lg border bg-card">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Proveedor</TableHead>
                        <TableHead>Total</TableHead>
                        <TableHead>Moneda</TableHead>
                        <TableHead>Estado</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {quotes.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={4} className="text-center text-muted-foreground py-8">Sin cotizaciones</TableCell>
                        </TableRow>
                      )}
                      {quotes.map((q: any) => (
                        <TableRow key={q.id}>
                          <TableCell>{q.supplier_name}</TableCell>
                          <TableCell className="font-mono">{formatCLP(q.total)}</TableCell>
                          <TableCell>{q.currency}</TableCell>
                          <TableCell><StatusBadge status={q.status} /></TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {extractedItems && (
                  <Card>
                    <CardHeader><CardTitle className="text-base">Ítems extraídos</CardTitle></CardHeader>
                    <CardContent className="p-0">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Descripción</TableHead>
                            <TableHead>Precio</TableHead>
                            <TableHead>Confianza</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {extractedItems.map((it: any, i: number) => (
                            <TableRow key={i}>
                              <TableCell>{it.description}</TableCell>
                              <TableCell className="font-mono">{it.price}</TableCell>
                              <TableCell>{it.confidence ? `${(it.confidence * 100).toFixed(0)}%` : "-"}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="analysis" className="mt-4 space-y-4">
                <Button onClick={() => analyzeMut.mutate(undefined, { onSuccess: () => { toast.success("Análisis completado"); refetch(); } })} disabled={analyzeMut.isPending} className="gap-2">
                  <Brain className="h-4 w-4" /> Analizar con IA
                </Button>

                {analysisMatrix && (
                  <Card>
                    <CardHeader><CardTitle className="text-base">Matriz comparativa</CardTitle></CardHeader>
                    <CardContent>
                      <div className="overflow-x-auto">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Ítem</TableHead>
                              {analysisMatrix.suppliers?.map((s: string) => (
                                <TableHead key={s}>{s}</TableHead>
                              ))}
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {analysisMatrix.rows?.map((row: any, i: number) => (
                              <TableRow key={i}>
                                <TableCell className="font-medium">{row.item}</TableCell>
                                {row.prices?.map((p: any, j: number) => (
                                  <TableCell key={j} className="font-mono">{p != null ? formatCLP(p) : "-"}</TableCell>
                                ))}
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {recommendation && (
                  <Card className="border-accent">
                    <CardHeader><CardTitle className="text-base text-accent">Recomendación IA</CardTitle></CardHeader>
                    <CardContent>
                      <p className="text-sm">{recommendation}</p>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="suppliers" className="mt-4 space-y-3">
                {rfqItems.length === 0 && (
                  <p className="text-sm text-muted-foreground">Este RFQ no tiene ítems todavía.</p>
                )}
                {rfqItems.map((item: any) => {
                  const assignedIds: string[] = item.supplier_ids || [];
                  return (
                    <Card key={item.id}>
                      <CardHeader className="pb-2">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <CardTitle className="text-sm font-semibold">{item.description}</CardTitle>
                            <p className="text-xs text-muted-foreground mt-0.5">
                              {item.quantity} {item.unit}
                            </p>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="pt-0 space-y-3">
                        {/* Assigned supplier badges */}
                        {assignedIds.length > 0 && (
                          <div className="flex flex-wrap gap-1.5">
                            {assignedIds.map((sid: string) => {
                              const sup = supplierList.find((s: any) => s.id === sid);
                              return (
                                <span
                                  key={sid}
                                  className="inline-flex items-center gap-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200 px-2.5 py-0.5 text-xs font-medium"
                                >
                                  {sup?.name ?? sid.slice(0, 8)}
                                  <button
                                    className="ml-0.5 hover:text-blue-900 font-bold leading-none"
                                    title="Quitar proveedor"
                                    disabled={setSuppliersMut.isPending}
                                    onClick={() =>
                                      setSuppliersMut.mutate({
                                        item_id: item.id,
                                        supplier_ids: assignedIds.filter((s) => s !== sid),
                                      })
                                    }
                                  >
                                    ×
                                  </button>
                                </span>
                              );
                            })}
                          </div>
                        )}

                        {/* Add supplier dropdown */}
                        <div className="flex gap-2">
                          <Select
                            onValueChange={(newSupplierId) => {
                              if (!newSupplierId || assignedIds.includes(newSupplierId)) return;
                              setSuppliersMut.mutate({
                                item_id: item.id,
                                supplier_ids: [...assignedIds, newSupplierId],
                              });
                            }}
                          >
                            <SelectTrigger className="w-56 h-8 text-xs">
                              <SelectValue placeholder="+ Agregar proveedor" />
                            </SelectTrigger>
                            <SelectContent>
                              {supplierList
                                .filter((s: any) => !assignedIds.includes(s.id))
                                .map((s: any) => (
                                  <SelectItem key={s.id} value={s.id} className="text-xs">
                                    {s.name}
                                  </SelectItem>
                                ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </TabsContent>

              <TabsContent value="emails" className="mt-4 space-y-4">
                {/* Add supplier to RFQ */}
                <div className="flex gap-2">
                  <Select value={selectedSupplierId} onValueChange={setSelectedSupplierId}>
                    <SelectTrigger className="w-64"><SelectValue placeholder="Seleccionar proveedor" /></SelectTrigger>
                    <SelectContent>
                      {supplierList.map((s: any) => (
                        <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    disabled={!selectedSupplierId || addSupplierMut.isPending}
                    onClick={() => {
                      addSupplierMut.mutate(selectedSupplierId, {
                        onSuccess: () => {
                          toast.success("Proveedor agregado");
                          setSelectedSupplierId("");
                        },
                      });
                    }}
                  >
                    Agregar a RFQ
                  </Button>
                </div>

                {/* Table of assigned suppliers */}
                {quotes.length > 0 && (
                  <>
                    <div className="rounded-lg border bg-card">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Proveedor</TableHead>
                            <TableHead>Email</TableHead>
                            <TableHead>Estado</TableHead>
                            <TableHead>Acciones</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {quotes.map((q: any) => {
                            const supplier = supplierList.find((s: any) => s.id === q.supplier_id);
                            const emailStatus = data?.email_status;
                            const log = Array.isArray(emailStatus)
                              ? emailStatus.find((l: any) => l.supplier_id === q.supplier_id)
                              : undefined;
                            return (
                              <TableRow key={q.id}>
                                <TableCell>{supplier?.name ?? "Proveedor"}</TableCell>
                                <TableCell className="text-sm text-muted-foreground">{supplier?.email ?? "—"}</TableCell>
                                <TableCell>
                                  {log ? <StatusBadge status={log.status} /> : <span className="text-xs text-muted-foreground">Sin enviar</span>}
                                </TableCell>
                                <TableCell>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    disabled={emailMut.isPending}
                                    onClick={() =>
                                      emailMut.mutate([q.supplier_id], {
                                        onSuccess: () => toast.success("Email enviado"),
                                      })
                                    }
                                    className="gap-1"
                                  >
                                    <Mail className="h-3 w-3" /> Enviar
                                  </Button>
                                </TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </div>

                    {/* Send to all */}
                    <Button
                      onClick={() =>
                        emailMut.mutate(
                          quotes.map((q: any) => q.supplier_id),
                          { onSuccess: () => toast.success("Emails enviados a todos") }
                        )
                      }
                      disabled={emailMut.isPending}
                      className="gap-2"
                    >
                      <Mail className="h-4 w-4" /> Enviar a todos
                    </Button>
                  </>
                )}

                {quotes.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    Agrega proveedores para poder enviarles la solicitud de cotización.
                  </p>
                )}
              </TabsContent>
            </Tabs>
          </>
        )}
      </div>

      <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Subir cotización</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <Select value={selectedSupplier} onValueChange={setSelectedSupplier}>
              <SelectTrigger><SelectValue placeholder="Seleccionar proveedor" /></SelectTrigger>
              <SelectContent>
                {supplierList.map((s: any) => (
                  <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <input ref={fileRef} type="file" accept=".pdf,image/*" className="text-sm" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setUploadOpen(false)}>Cancelar</Button>
            <Button
              disabled={!selectedSupplier || uploadMut.isPending}
              onClick={handleUpload}
            >
              {uploadMut.isPending ? "Subiendo..." : "Subir y procesar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
