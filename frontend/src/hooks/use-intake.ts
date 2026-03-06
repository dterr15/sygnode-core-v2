import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useIntakeList(status: string) {
  return useQuery({
    queryKey: ["intake", status],
    queryFn: () => api.get(`/api/v2/intake?status=${status}`),
  });
}

export function useIntakeDetail(id: string | undefined) {
  return useQuery({
    queryKey: ["intake", id],
    queryFn: () => api.get(`/api/v2/intake/${id}`),
    enabled: !!id,
  });
}

export function useIntakeApprove() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post(`/api/v2/intake/${id}/approve`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["intake"] }),
  });
}

export function useIntakeReject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.post(`/api/v2/intake/${id}/reject`, { reason }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["intake"] }),
  });
}

export function useIntakeTransition(id: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (to_status: string) =>
      api.post(`/api/v2/intake/${id}/transition`, { to_status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["intake"] }),
  });
}

export function useIntakePaste() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ text, source }: { text: string; source: string }) =>
      api.post("/api/v2/intake/paste", { text, source }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["intake"] }),
  });
}

export function useIntakePatchItem(listId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ itemId, patch }: { itemId: string; patch: Record<string, any> }) =>
      api.patch(`/api/v2/intake/${listId}/items/${itemId}`, patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["intake", listId] }),
  });
}
