import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format ISO date string to DD/MM/YYYY (mercado chileno) */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "-";
  const d = iso.slice(0, 10); // "YYYY-MM-DD"
  const [y, m, day] = d.split("-");
  return `${day}/${m}/${y}`;
}

/** Format number as Chilean peso: $1.234.567 */
export function formatCLP(amount: number | null | undefined): string {
  if (amount == null) return "-";
  return amount.toLocaleString("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 });
}
