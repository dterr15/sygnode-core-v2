import { useEffect } from "react";
import { useUIStore } from "@/stores/ui-store";

export function OfflineBanner() {
  const { isOnline, setOnline } = useUIStore();

  useEffect(() => {
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, [setOnline]);

  if (isOnline) return null;

  return <div className="offline-banner">Sin conexión al servidor</div>;
}
