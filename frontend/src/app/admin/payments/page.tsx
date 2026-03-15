"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { adminApi } from "@/lib/api";
import type { Payment, PaymentStatus } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle, XCircle } from "lucide-react";

const statusLabels: Record<PaymentStatus, string> = {
  PENDING: "Pendiente",
  CONFIRMED: "Confirmado",
  REJECTED: "Rechazado",
  REFUNDED: "Reembolsado",
};

const statusColors: Record<PaymentStatus, string> = {
  PENDING: "bg-yellow-100 text-yellow-800",
  CONFIRMED: "bg-green-100 text-green-800",
  REJECTED: "bg-red-100 text-red-800",
  REFUNDED: "bg-slate-100 text-slate-800",
};

const methodLabels: Record<string, string> = {
  TRANSFER: "Transferencia",
  CASH: "Efectivo",
  GATEWAY: "Pasarela",
};

function formatCLP(amount: number) {
  return new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    minimumFractionDigits: 0,
  }).format(amount);
}

export default function PaymentsPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<PaymentStatus | "ALL">("ALL");

  const { data: payments, isLoading } = useQuery({
    queryKey: ["admin", "payments", statusFilter],
    queryFn: () =>
      adminApi.payments.list(statusFilter === "ALL" ? undefined : statusFilter),
  });

  const confirmMutation = useMutation({
    mutationFn: ({
      id,
      action,
    }: {
      id: string;
      action: "confirm" | "reject";
    }) => adminApi.payments.confirm(id, action),
    onSuccess: (_, { action }) => {
      toast.success(
        action === "confirm" ? "Pago confirmado" : "Pago rechazado"
      );
      queryClient.invalidateQueries({ queryKey: ["admin", "payments"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Pagos</h1>
          <p className="text-sm text-slate-500">
            Gestiona los pagos de membresías
          </p>
        </div>
        <Select
          value={statusFilter}
          onValueChange={(v) => setStatusFilter(v as PaymentStatus | "ALL")}
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">Todos</SelectItem>
            <SelectItem value="PENDING">Pendientes</SelectItem>
            <SelectItem value="CONFIRMED">Confirmados</SelectItem>
            <SelectItem value="REJECTED">Rechazados</SelectItem>
            <SelectItem value="REFUNDED">Reembolsados</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="border rounded-lg bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Socio</TableHead>
              <TableHead>Monto</TableHead>
              <TableHead>Periodo</TableHead>
              <TableHead>Metodo</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>Fecha</TableHead>
              <TableHead className="text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell>
                    <Skeleton className="h-5 w-40" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-20" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-20" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-24" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-20" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-24" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-8 w-16 ml-auto" />
                  </TableCell>
                </TableRow>
              ))
            ) : payments?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-slate-500">
                  No hay pagos
                </TableCell>
              </TableRow>
            ) : (
              payments?.map((p: Payment) => (
                <TableRow key={p.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{p.membership.user.full_name}</p>
                      <p className="text-sm text-slate-500">{p.membership.user.email}</p>
                    </div>
                  </TableCell>
                  <TableCell className="font-medium">
                    {formatCLP(p.amount_clp)}
                  </TableCell>
                  <TableCell>
                    {p.period_month && p.period_year
                      ? `${String(p.period_month).padStart(2, "0")}/${p.period_year}`
                      : "-"}
                  </TableCell>
                  <TableCell>{methodLabels[p.payment_method]}</TableCell>
                  <TableCell>
                    <Badge variant="secondary" className={statusColors[p.status]}>
                      {statusLabels[p.status]}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {new Date(p.payment_date).toLocaleDateString("es-CL")}
                  </TableCell>
                  <TableCell className="text-right">
                    {p.status === "PENDING" && (
                      <div className="flex justify-end gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-green-600 hover:text-green-700 hover:bg-green-50"
                          onClick={() =>
                            confirmMutation.mutate({ id: p.id, action: "confirm" })
                          }
                          disabled={confirmMutation.isPending}
                        >
                          <CheckCircle className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          onClick={() =>
                            confirmMutation.mutate({ id: p.id, action: "reject" })
                          }
                          disabled={confirmMutation.isPending}
                        >
                          <XCircle className="h-4 w-4" />
                        </Button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
