import { QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError } from "./api";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (error instanceof ApiError && [401, 403, 404].includes(error.status)) return false;
        return failureCount < 2;
      },
      staleTime: 30_000,
    },
    mutations: {
      onError: (error) => {
        if (error instanceof ApiError) {
          switch (error.status) {
            case 403:
              toast.error("Sin permisos para esta acción");
              break;
            case 409:
              toast.error(error.detail);
              break;
            case 500:
              toast.error("Error del servidor, intenta nuevamente");
              break;
            default:
              if (error.status !== 422) toast.error(error.detail);
          }
        } else {
          toast.error("Error de conexión");
        }
      },
    },
  },
});
