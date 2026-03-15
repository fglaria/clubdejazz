"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { adminApi } from "@/lib/api";
import type { Membership, MembershipStatus } from "@/lib/types";
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

const statusLabels: Record<MembershipStatus, string> = {
  PENDING: "Pendiente",
  ACTIVE: "Activo",
  SUSPENDED: "Suspendido",
  EXPIRED: "Expirado",
  CANCELLED: "Cancelado",
};

const statusColors: Record<MembershipStatus, string> = {
  PENDING: "bg-yellow-100 text-yellow-800",
  ACTIVE: "bg-green-100 text-green-800",
  SUSPENDED: "bg-orange-100 text-orange-800",
  EXPIRED: "bg-slate-100 text-slate-800",
  CANCELLED: "bg-red-100 text-red-800",
};

export default function MembersPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<MembershipStatus | "ALL">(
    "ALL"
  );

  const { data: memberships, isLoading } = useQuery({
    queryKey: ["admin", "memberships", statusFilter],
    queryFn: () =>
      adminApi.memberships.list(
        statusFilter === "ALL" ? undefined : statusFilter
      ),
  });

  const { data: pendingCount } = useQuery({
    queryKey: ["admin", "memberships", "pendingCount"],
    queryFn: () => adminApi.memberships.pendingCount(),
  });

  const reviewMutation = useMutation({
    mutationFn: ({
      id,
      action,
    }: {
      id: string;
      action: "approve" | "reject";
    }) => adminApi.memberships.review(id, action),
    onSuccess: (_, { action }) => {
      toast.success(
        action === "approve" ? "Solicitud aprobada" : "Solicitud rechazada"
      );
      queryClient.invalidateQueries({ queryKey: ["admin", "memberships"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Socios</h1>
          <p className="text-sm text-slate-500">
            {pendingCount?.count
              ? `${pendingCount.count} solicitud(es) pendiente(s)`
              : "Gestiona las membresías del club"}
          </p>
        </div>
        <Select
          value={statusFilter}
          onValueChange={(v) => setStatusFilter(v as MembershipStatus | "ALL")}
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">Todos</SelectItem>
            <SelectItem value="PENDING">Pendientes</SelectItem>
            <SelectItem value="ACTIVE">Activos</SelectItem>
            <SelectItem value="SUSPENDED">Suspendidos</SelectItem>
            <SelectItem value="EXPIRED">Expirados</SelectItem>
            <SelectItem value="CANCELLED">Cancelados</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="border rounded-lg bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Socio</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>Fecha inicio</TableHead>
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
            ) : memberships?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-slate-500">
                  No hay membresías
                </TableCell>
              </TableRow>
            ) : (
              memberships?.map((m: Membership) => (
                <TableRow key={m.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{m.user.full_name}</p>
                      <p className="text-sm text-slate-500">{m.user.email}</p>
                    </div>
                  </TableCell>
                  <TableCell>{m.membership_type.name}</TableCell>
                  <TableCell>
                    <Badge variant="secondary" className={statusColors[m.status]}>
                      {statusLabels[m.status]}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {new Date(m.start_date).toLocaleDateString("es-CL")}
                  </TableCell>
                  <TableCell className="text-right">
                    {m.status === "PENDING" && (
                      <div className="flex justify-end gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-green-600 hover:text-green-700 hover:bg-green-50"
                          onClick={() =>
                            reviewMutation.mutate({ id: m.id, action: "approve" })
                          }
                          disabled={reviewMutation.isPending}
                        >
                          <CheckCircle className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          onClick={() =>
                            reviewMutation.mutate({ id: m.id, action: "reject" })
                          }
                          disabled={reviewMutation.isPending}
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
