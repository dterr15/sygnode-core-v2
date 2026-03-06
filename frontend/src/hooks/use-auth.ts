import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useCurrentUser() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => api.get("/api/v2/auth/me"),
    retry: false,
  });
}
