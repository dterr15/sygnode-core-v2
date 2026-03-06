import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { AppShell } from "@/components/layout/AppShell";
import { PageLoader } from "@/components/PageLoader";
import { PageError } from "@/components/PageError";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { useState, useEffect } from "react";

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ organization_name: "", default_currency: "", timezone: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get("/api/v2/settings"),
  });

  useEffect(() => {
    if (data) {
      setForm({
        organization_name: data.organization_name || "",
        default_currency: data.default_currency || "",
        timezone: data.timezone || "",
      });
    }
  }, [data]);

  const saveMut = useMutation({
    mutationFn: () => api.patch("/api/v2/settings", form),
    onSuccess: () => {
      toast.success("Configuración guardada");
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 422 && err.errors) {
        const mapped: Record<string, string> = {};
        for (const [k, v] of Object.entries(err.errors)) mapped[k] = Array.isArray(v) ? v[0] : v;
        setErrors(mapped);
      }
    },
  });

  return (
    <AppShell>
      <div className="space-y-4 max-w-lg">
        <h1 className="text-2xl font-bold">Configuración</h1>

        {isLoading && <PageLoader />}
        {isError && <PageError onRetry={refetch} />}

        {data && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Organización</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                { key: "organization_name", label: "Nombre de organización" },
                { key: "default_currency", label: "Moneda predeterminada" },
                { key: "timezone", label: "Zona horaria" },
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
              <Button onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
                Guardar
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
