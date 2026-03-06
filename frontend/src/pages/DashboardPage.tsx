import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useCurrentUser } from "@/hooks/use-auth";
import { AppShell } from "@/components/layout/AppShell";
import { PageLoader } from "@/components/PageLoader";
import { PageError } from "@/components/PageError";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Inbox, FileText, Scale, ShieldCheck } from "lucide-react";

export default function DashboardPage() {
  const { data: user } = useCurrentUser();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.get("/api/v2/dashboard"),
  });

  return (
    <AppShell>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>

        {isLoading && <PageLoader />}
        {isError && <PageError onRetry={refetch} />}

        {data && (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: "Intake Pendiente", value: data.intake_pending ?? 0, icon: Inbox, color: "text-warning" },
                { label: "RFQs Activos", value: data.rfqs_active ?? 0, icon: FileText, color: "text-primary" },
                { label: "Casos Abiertos", value: data.cases_open ?? 0, icon: Scale, color: "text-accent" },
                { label: "Validaciones ML", value: data.validations_pending ?? 0, icon: ShieldCheck, color: "text-info" },
              ].map((m) => (
                <Card key={m.label}>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">{m.label}</CardTitle>
                    <m.icon className={`h-5 w-5 ${m.color}`} />
                  </CardHeader>
                  <CardContent>
                    <p className="text-3xl font-bold">{m.value}</p>
                  </CardContent>
                </Card>
              ))}
            </div>

            {data.work_queue && data.work_queue.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Cola de trabajo</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {data.work_queue.map((item: any, i: number) => (
                      <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
                        <span className="text-sm">{item.title}</span>
                        <span className="text-xs text-muted-foreground">{item.type}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
