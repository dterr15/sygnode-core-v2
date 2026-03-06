import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useClientList() {
  return useQuery({
    queryKey: ["clients"],
    queryFn: () => api.get("/api/v2/clients"),
  });
}

export function useClientCreate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, any>) =>
      api.post("/api/v2/clients", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["clients"] }),
  });
}
