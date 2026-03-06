import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useSupplierList() {
  return useQuery({
    queryKey: ["suppliers"],
    queryFn: () => api.get("/api/v2/suppliers"),
  });
}

export function useSupplierCreate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; email?: string; phone?: string; city?: string; region?: string; categories?: string[]; rut?: string }) =>
      api.post("/api/v2/suppliers", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["suppliers"] }),
  });
}
