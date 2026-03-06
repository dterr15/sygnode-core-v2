import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useIntakeDetail, useIntakePatchItem, useIntakeTransition, useIntakeApprove } from "@/hooks/use-intake";
import { ApiError } from "@/lib/api";
import { AppShell } from "@/components/layout/AppShell";
import { PageLoader } from "@/components/PageLoader";
import { PageError } from "@/components/PageError";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { ArrowLeft } from "lucide-react";
import { formatDate } from "@/lib/utils";

export default function IntakeDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [editingCell, setEditingCell] = useState<{ itemId: string; field: string } | null>(null);
  const [editValue, setEditValue] = useState("");

  const { data, isLoading, isError, refetch } = useIntakeDetail(id);
  const patchItem = useIntakePatchItem(id);
  const transitionMut = useIntakeTransition(id);
  const approveMut = useIntakeApprove();

  const startEdit = (itemId: string, field: string, currentValue: string) => {
    setEditingCell({ itemId, field });
    setEditValue(currentValue);
  };

  const commitEdit = () => {
    if (editingCell) {
      patchItem.mutate(
        { itemId: editingCell.itemId, patch: { [editingCell.field]: editValue } },
        {
          onSuccess: () => setEditingCell(null),
          onError: (err) => {
            if (err instanceof ApiError && err.status === 422) toast.error("Valor inválido");
          },
        }
      );
    }
  };

  // Backend returns { list: IntakeListOut, items: IntakeItemOut[] }
  const list = data?.list;
  const items = data?.items || [];

  const isPending = list?.validation_status === "STAGED_PENDING_VALIDATION";
  const isApproved = list?.validation_status === "APPROVED_GENERATED";

  return (
    <AppShell>
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={() => navigate("/intake")} className="gap-1">
          <ArrowLeft className="h-4 w-4" /> Volver
        </Button>

        {isLoading && <PageLoader />}
        {isError && <PageError onRetry={refetch} />}

        {list && (
          <>
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-xl">{list.title}</CardTitle>
                  <StatusBadge status={list.validation_status || list.status} />
                </div>
                <div className="flex gap-4 text-sm text-muted-foreground mt-1">
                  <span>Fuente: {list.source}</span>
                  <span>Fecha: {formatDate(list.created_at)}</span>
                  {list.from_name && <span>De: {list.from_name}</span>}
                </div>
                {isApproved && list.validated_by_user_id && (
                  <p className="text-sm text-success mt-2">
                    Aprobado el {formatDate(list.validated_at)}
                  </p>
                )}
                {list.rejected_reason && (
                  <p className="text-sm text-destructive mt-2">
                    Motivo rechazo: {list.rejected_reason}
                  </p>
                )}
              </CardHeader>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Ítems del requerimiento</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Descripción</TableHead>
                      <TableHead>Cantidad</TableHead>
                      <TableHead>UOM</TableHead>
                      <TableHead>Confianza</TableHead>
                      <TableHead>Confirmado</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {items.map((item: any) => (
                      <TableRow key={item.id}>
                        {["description", "quantity", "uom"].map((field) => (
                          <TableCell
                            key={field}
                            className="cursor-pointer"
                            onClick={() => startEdit(item.id, field, String(item[field] ?? ""))}
                          >
                            {editingCell?.itemId === item.id && editingCell.field === field ? (
                              <Input
                                autoFocus
                                value={editValue}
                                onChange={(e) => setEditValue(e.target.value)}
                                onBlur={commitEdit}
                                onKeyDown={(e) => e.key === "Enter" && commitEdit()}
                                className="h-8"
                              />
                            ) : (
                              item[field] ?? "-"
                            )}
                          </TableCell>
                        ))}
                        <TableCell>
                          {item.confidence_score != null
                            ? `${(Number(item.confidence_score) * 100).toFixed(0)}%`
                            : "-"}
                        </TableCell>
                        <TableCell>{item.is_confirmed ? "✓" : "—"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            <div className="flex gap-3">
              {isPending && (
                <>
                  <Button
                    onClick={() =>
                      approveMut.mutate(list.id, {
                        onSuccess: () => {
                          toast.success("Aprobado");
                          refetch();
                        },
                      })
                    }
                    disabled={approveMut.isPending}
                  >
                    Aprobar
                  </Button>
                  <Button variant="destructive" onClick={() => navigate(`/intake`)}>
                    Rechazar
                  </Button>
                </>
              )}
              {isApproved && (
                <Button
                  onClick={() =>
                    transitionMut.mutate("EN_COTIZACION", {
                      onSuccess: () => {
                        toast.success("Promovido a RFQ");
                        navigate("/rfqs");
                      },
                    })
                  }
                  disabled={transitionMut.isPending}
                >
                  Promover a RFQ
                </Button>
              )}
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
