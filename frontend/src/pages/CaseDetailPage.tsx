import { useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useCaseDetail, useCaseTransition, useCaseUploadPO, useCaseEvidencePack, useCaseJustifyVariance } from "@/hooks/use-cases";
import { useCurrentUser } from "@/hooks/use-auth";
import { AppShell } from "@/components/layout/AppShell";
import { PageLoader } from "@/components/PageLoader";
import { PageError } from "@/components/PageError";
import { StatusBadge } from "@/components/StatusBadge";
import { SeverityBadge } from "@/components/SeverityBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { toast } from "sonner";
import { ArrowLeft, Clock, FileText, AlertTriangle, Package, Lock, Download } from "lucide-react";
import { formatDate, formatCLP } from "@/lib/utils";

export default function CaseDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [justification, setJustification] = useState("");
  const [evidencePackOpen, setEvidencePackOpen] = useState(false);
  const [evidencePackData, setEvidencePackData] = useState<any>(null);

  const { data: user } = useCurrentUser();
  const { data, isLoading, isError, refetch } = useCaseDetail(id);
  const freezeMut = useCaseTransition(id);
  const uploadPOMut = useCaseUploadPO(id);
  const evidencePackMut = useCaseEvidencePack(id);
  const justifyMut = useCaseJustifyVariance(id);

  // Backend returns { case, timeline, evidences, fulfillment, chain_intact }
  const caseData = data?.case;
  const timeline = data?.timeline || [];
  const evidences = data?.evidences || [];
  const fulfillment = data?.fulfillment;
  const chainIntact = data?.chain_intact;

  const isFrozen = caseData?.status === "FROZEN";
  const isOpen = caseData?.status === "OPEN";
  const isAdmin = user?.role === "admin_org";
  const hasFulfillment = !!fulfillment;
  const requiresJustification = fulfillment?.requires_justification;

  return (
    <AppShell>
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={() => navigate("/cases")} className="gap-1">
          <ArrowLeft className="h-4 w-4" /> Volver
        </Button>

        {isLoading && <PageLoader />}
        {isError && <PageError onRetry={refetch} />}

        {caseData && (
          <>
            {/* Header */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-xl font-mono">{caseData.case_reference || caseData.id?.slice(0, 12)}</CardTitle>
                  <div className="flex gap-2">
                    <StatusBadge status={caseData.criticality} />
                    <StatusBadge status={caseData.status} />
                  </div>
                </div>
                {caseData.frozen_first_at && (
                  <p className="text-xs text-muted-foreground">Congelado: {formatDate(caseData.frozen_first_at)}</p>
                )}
                {chainIntact !== undefined && (
                  <p className={`text-xs ${chainIntact ? "text-success" : "text-destructive"}`}>
                    Cadena de integridad: {chainIntact ? "✓ Intacta" : "✗ Rota"}
                  </p>
                )}
              </CardHeader>
            </Card>

            {/* Variance warning */}
            {requiresJustification && fulfillment.reconciliation_status === "PENDING" && (
              <div className="flex items-center gap-3 p-4 rounded-lg border border-destructive bg-destructive/10">
                <AlertTriangle className="h-5 w-5 text-destructive shrink-0" />
                <span className="text-sm font-medium text-destructive">
                  Se requiere justificación de varianza obligatoria
                </span>
              </div>
            )}

            {/* Timeline */}
            <Card>
              <CardHeader><CardTitle className="text-base flex items-center gap-2"><Clock className="h-4 w-4" /> Timeline</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {timeline.map((event: any) => (
                    <div key={event.id} className="flex gap-3 border-l-2 border-border pl-4 pb-3">
                      <div className="flex-1">
                        <p className="text-sm font-medium">{event.event_description}</p>
                        <div className="flex gap-3 text-xs text-muted-foreground mt-1">
                          <span>{event.event_type}</span>
                          {event.actor_role && <span>{event.actor_role}</span>}
                          <span>{formatDate(event.event_timestamp)} {event.event_timestamp?.slice(11, 16)}</span>
                          <span className="font-mono">{event.event_hash?.slice(0, 8)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                  {timeline.length === 0 && <p className="text-sm text-muted-foreground">Sin eventos</p>}
                </div>
              </CardContent>
            </Card>

            {/* Evidences */}
            <Card>
              <CardHeader><CardTitle className="text-base flex items-center gap-2"><FileText className="h-4 w-4" /> Evidencias</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {evidences.map((ev: any) => (
                    <div key={ev.id} className="flex items-center justify-between py-2 border-b last:border-0">
                      <div>
                        <p className="text-sm font-medium">{ev.filename}</p>
                        <p className="text-xs text-muted-foreground">
                          {ev.evidence_type} • SHA256: {ev.sha256_hash?.slice(0, 8)} • {formatDate(ev.uploaded_at)}
                        </p>
                      </div>
                    </div>
                  ))}
                  {evidences.length === 0 && <p className="text-sm text-muted-foreground">Sin evidencias</p>}
                </div>
              </CardContent>
            </Card>

            {/* Fulfillment / PO Section */}
            <Card>
              <CardHeader><CardTitle className="text-base flex items-center gap-2"><Package className="h-4 w-4" /> Orden de Compra</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                {!hasFulfillment && !isFrozen && (
                  <div className="space-y-2">
                    <input ref={fileRef} type="file" className="text-sm" />
                    <Button
                      size="sm"
                      onClick={() => {
                        const file = fileRef.current?.files?.[0];
                        if (file) uploadPOMut.mutate(file, { onSuccess: () => { toast.success("OC subida"); refetch(); } });
                      }}
                      disabled={uploadPOMut.isPending}
                    >
                      Subir OC
                    </Button>
                  </div>
                )}
                {hasFulfillment && (
                  <div className="space-y-2 text-sm">
                    <div className="grid grid-cols-2 gap-2">
                      {fulfillment.po_number && <div>N° OC: <strong>{fulfillment.po_number}</strong></div>}
                      {fulfillment.total_amount != null && <div>Monto: <strong className="font-mono">{formatCLP(fulfillment.total_amount)} {fulfillment.currency !== "CLP" ? fulfillment.currency : ""}</strong></div>}
                      {fulfillment.delta_pct != null && <div>Delta: <strong>{fulfillment.delta_pct}%</strong></div>}
                      <div>Reconciliación: <StatusBadge status={fulfillment.reconciliation_status} /></div>
                    </div>
                    {fulfillment.justification_text && (
                      <p className="text-xs text-muted-foreground mt-2">Justificación: {fulfillment.justification_text}</p>
                    )}
                    {requiresJustification && fulfillment.reconciliation_status !== "VARIANCE_JUSTIFIED" && (
                      <div className="space-y-2 mt-3">
                        <Textarea
                          placeholder="Justificación de varianza (mínimo 50 caracteres)..."
                          value={justification}
                          onChange={(e) => setJustification(e.target.value)}
                        />
                        <Button
                          size="sm"
                          disabled={justification.length < 50 || justifyMut.isPending}
                          onClick={() => justifyMut.mutate(justification, { onSuccess: () => { toast.success("Justificación enviada"); setJustification(""); refetch(); } })}
                        >
                          Justificar varianza
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Actions */}
            <div className="flex gap-3">
              {isOpen && isAdmin && (
                <Button
                  onClick={() => freezeMut.mutate("FROZEN", { onSuccess: () => { toast.success("Caso congelado"); refetch(); } })}
                  disabled={freezeMut.isPending || (caseData.evidence_count === 0)}
                  className="gap-2"
                >
                  <Lock className="h-4 w-4" /> Congelar caso
                </Button>
              )}
              {isFrozen && (
                <Button
                  variant="outline"
                  onClick={() => evidencePackMut.mutate(undefined, {
                    onSuccess: (result) => {
                      setEvidencePackData(result);
                      setEvidencePackOpen(true);
                    },
                  })}
                  className="gap-2"
                >
                  <Download className="h-4 w-4" /> Evidence Pack
                </Button>
              )}
            </div>
          </>
        )}
      </div>

      <Dialog open={evidencePackOpen} onOpenChange={setEvidencePackOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>Evidence Pack</DialogTitle></DialogHeader>
          <pre className="text-xs bg-muted p-4 rounded-lg overflow-auto max-h-96">
            {JSON.stringify(evidencePackData, null, 2)}
          </pre>
          <Button variant="outline" onClick={() => {
            const blob = new Blob([JSON.stringify(evidencePackData, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `evidence-pack-${id}.json`;
            a.click();
          }}>
            Descargar JSON
          </Button>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
