import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useCaseList() {
  return useQuery({
    queryKey: ["cases"],
    queryFn: () => api.get("/api/v2/cases"),
  });
}

export function useCaseDetail(id: string | undefined) {
  return useQuery({
    queryKey: ["case", id],
    queryFn: () => api.get(`/api/v2/cases/${id}`),
    enabled: !!id,
  });
}

export function useCaseTransition(id: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (to_status: string) =>
      api.post(`/api/v2/cases/${id}/transition`, { to_status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["case", id] }),
  });
}

export function useCaseUploadPO(id: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return api.post(`/api/v2/cases/${id}/upload-po`, fd);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["case", id] }),
  });
}

export function useCaseVerifyChain(id: string | undefined) {
  return useQuery({
    queryKey: ["case", id, "verify-chain"],
    queryFn: () => api.get(`/api/v2/cases/${id}/verify-chain`),
    enabled: false,
  });
}

export function useCaseEvidencePack(id: string | undefined) {
  return useMutation({
    mutationFn: () => api.get(`/api/v2/cases/${id}/evidence-pack`),
  });
}

export function useCaseJustifyVariance(id: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (justification_text: string) =>
      api.post(`/api/v2/cases/${id}/justify-variance`, { justification_text }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["case", id] }),
  });
}
