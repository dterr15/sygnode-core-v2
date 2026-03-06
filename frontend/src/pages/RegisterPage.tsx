import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { toast } from "sonner";

export default function RegisterPage() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    rut_organizacion: "",
    nombre_organizacion: "",
    city: "",
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const navigate = useNavigate();

  const set = (key: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrors({});
    try {
      await api.post("/api/v2/auth/register", form);
      toast.success("Cuenta creada exitosamente");
      navigate("/login");
    } catch (err) {
      if (err instanceof ApiError && err.status === 422 && err.errors) {
        const mapped: Record<string, string> = {};
        for (const [k, v] of Object.entries(err.errors)) mapped[k] = Array.isArray(v) ? v[0] : v;
        setErrors(mapped);
      } else if (err instanceof ApiError) {
        toast.error(err.detail);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm shadow-lg">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold text-primary">Crear cuenta</CardTitle>
          <CardDescription>Registra tu organización</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {[
              { key: "nombre_organizacion", label: "Nombre de organización", type: "text" },
              { key: "rut_organizacion", label: "RUT organización", type: "text" },
              { key: "name", label: "Nombre completo", type: "text" },
              { key: "email", label: "Correo electrónico", type: "email" },
              { key: "password", label: "Contraseña", type: "password" },
              { key: "city", label: "Ciudad (opcional)", type: "text" },
            ].map(({ key, label, type }) => (
              <div className="space-y-2" key={key}>
                <Label>{label}</Label>
                <Input
                  type={type}
                  value={(form as any)[key]}
                  onChange={set(key)}
                  required={key !== "city"}
                />
                {errors[key] && <p className="text-xs text-destructive">{errors[key]}</p>}
              </div>
            ))}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Registrando..." : "Registrarse"}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              ¿Ya tienes cuenta?{" "}
              <a href="/login" className="text-primary hover:underline">Ingresar</a>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
