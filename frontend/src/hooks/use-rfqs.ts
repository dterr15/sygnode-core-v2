import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useRFQList() {
  return useQuery({
    queryKey: ["rfqs"],
    queryFn: () => api.get("/api/v2/rfqs"),
  });
}

export function useRFQDetail(id: string | undefined) {
  return useQuery({
    queryKey: ["rfq", id],
    queryFn: () => api.get(`/api/v2/rfqs/${id}`),
    enabled: !!id,
  });
}

export function useRFQCreate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { title: string; description?: string; items: any[]; client_id?: string }) =>
      api.post("/api/v2/rfqs", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rfqs"] }),
  });
}

export function useRFQAnalyze(id: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post(`/api/v2/rfqs/${id}/analyze`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rfq", id] }),
  });
}

export function useRFQSendEmails(id: string | undefined) {
  return useMutation({
    mutationFn: (supplier_ids: string[]) =>
      api.post(`/api/v2/rfqs/${id}/send-emails`, { supplier_ids }),
  });
}

export function useQuoteUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ file, rfq_id, supplier_id }: { file: File; rfq_id: string; supplier_id: string }) => {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("rfq_id", rfq_id);
      fd.append("supplier_id", supplier_id);
      return api.post("/api/v2/cotizaciones/upload", fd);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rfq"] }),
  });
}

export function useQuoteProcess() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (docId: string) => api.post(`/api/v2/cotizaciones/${docId}/process`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rfq"] }),
  });
}
