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
import { ChevronLeft, ChevronRight, LayoutList, CalendarDays } from "lucide-react";

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

const MONTH_ABBR = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

/** Returns array of {month, year} for the 6 visible columns, index 0 = leftmost (most recent). */
function getVisibleMonths(offset: number): Array<{ month: number; year: number }> {
  const now = new Date();
  return Array.from({ length: 6 }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() - offset - i, 1);
    return { month: d.getMonth() + 1, year: d.getFullYear() };
  });
}

/** Returns months-ago distance of the earliest payment with a period, or 0 if none. */
function earliestMonthsAgo(payments: Payment[]): number {
  const now = new Date();
  let maxDist = 0;
  for (const p of payments) {
    if (p.period_month && p.period_year) {
      const dist = (now.getFullYear() - p.period_year) * 12 + (now.getMonth() + 1 - p.period_month);
      if (dist > maxDist) maxDist = dist;
    }
  }
  return maxDist;
}

/** Counts consecutive months from current month backwards with no CONFIRMED payment. */
function computeUnpaidStreak(confirmedKeys: Set<string>): number {
  const now = new Date();
  let streak = 0;
  let y = now.getFullYear();
  let m = now.getMonth() + 1;
  for (let i = 0; i < 120; i++) {
    const key = `${y}-${String(m).padStart(2, "0")}`;
    if (confirmedKeys.has(key)) break;
    streak++;
    m--;
    if (m === 0) { m = 12; y--; }
  }
  return streak;
}

type MemberRow = {
  membershipId: string;
  memberNumber: number | null;
  fullName: string;
  startDate: string;
  paymentsByMonth: Map<string, Payment>; // key: "YYYY-MM"
  unpaidStreak: number;
};

/** Builds sorted member rows from a flat payments array. */
function buildMemberRows(payments: Payment[]): MemberRow[] {
  const map = new Map<string, MemberRow>();

  for (const p of payments) {
    if (!map.has(p.membership_id)) {
      map.set(p.membership_id, {
        membershipId: p.membership_id,
        memberNumber: p.membership.user.member_number,
        fullName: p.membership.user.full_name,
        startDate: p.membership.start_date,
        paymentsByMonth: new Map(),
        unpaidStreak: 0,
      });
    }
    if (p.period_month && p.period_year) {
      const key = `${p.period_year}-${String(p.period_month).padStart(2, "0")}`;
      map.get(p.membership_id)!.paymentsByMonth.set(key, p);
    }
  }

  // Compute streak for each member
  for (const row of map.values()) {
    const confirmed = new Set<string>();
    for (const [, p] of row.paymentsByMonth) {
      if (p.status === "CONFIRMED") confirmed.add(`${p.period_year}-${String(p.period_month).padStart(2, "0")}`);
    }
    row.unpaidStreak = computeUnpaidStreak(confirmed);
  }

  return Array.from(map.values()).sort((a, b) => {
    const na = a.memberNumber ?? 99999;
    const nb = b.memberNumber ?? 99999;
    return na - nb;
  });
}

/** Returns Tailwind classes for a calendar cell. */
function cellClass(
  payment: Payment | undefined,
  streak: number,
  monthKey: string,
  startDate: string
): string {
  // Pre-membership: before the month the membership started
  const [sy, sm] = startDate.split("-").map(Number);
  const [cy, cm] = monthKey.split("-").map(Number);
  if (cy < sy || (cy === sy && cm < sm)) {
    return "bg-slate-50";
  }

  if (!payment) {
    return streak <= 5
      ? "bg-orange-100 text-orange-700"
      : "bg-red-200 text-red-800";
  }

  switch (payment.status) {
    case "CONFIRMED": return "bg-green-100 text-green-700";
    case "PENDING":   return "bg-amber-100 text-amber-700";
    case "REJECTED":  return "bg-red-100 text-red-700";
    case "REFUNDED":  return "bg-slate-100 text-slate-500";
    default:          return "bg-slate-50";
  }
}

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

  const [viewMode, setViewMode] = useState<"table" | "calendar">("table");
  const [calendarOffset, setCalendarOffset] = useState(0);

  const { data: allPayments, isLoading: calendarLoading } = useQuery({
    queryKey: ["admin", "payments", "all"],
    queryFn: () => adminApi.payments.list(),
    enabled: viewMode === "calendar",
  });

  const visibleMonths = getVisibleMonths(calendarOffset);

  // Group visible months by year for the colspan header
  const yearGroups: Array<{ year: number; count: number }> = [];
  for (const { year } of visibleMonths) {
    const last = yearGroups[yearGroups.length - 1];
    if (last && last.year === year) { last.count++; }
    else { yearGroups.push({ year, count: 1 }); }
  }

  const memberRows = allPayments ? buildMemberRows(allPayments) : [];
  const maxOffset = allPayments ? Math.max(0, earliestMonthsAgo(allPayments) - 5) : 0;
  const canGoBack = calendarOffset < maxOffset;
  const canGoForward = calendarOffset > 0;

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Pagos</h1>
          <p className="text-sm text-slate-500">
            Gestiona los pagos de membresías
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex rounded-md border border-slate-200 overflow-hidden">
            <button
              className={`px-3 py-1.5 text-sm flex items-center gap-1.5 ${viewMode === "table" ? "bg-slate-900 text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`}
              onClick={() => setViewMode("table")}
            >
              <LayoutList className="h-4 w-4" />
              Tabla
            </button>
            <button
              className={`px-3 py-1.5 text-sm flex items-center gap-1.5 border-l border-slate-200 ${viewMode === "calendar" ? "bg-slate-900 text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`}
              onClick={() => setViewMode("calendar")}
            >
              <CalendarDays className="h-4 w-4" />
              Calendario
            </button>
          </div>
          {viewMode === "table" && (
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
          )}
        </div>
      </div>

      {viewMode === "table" && (
        <div className="border rounded-lg bg-white">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nombre</TableHead>
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
                    <TableCell className="font-medium">{p.membership.user.full_name}</TableCell>
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
      )}

      {viewMode === "calendar" && (
        <div>
          {/* Navigation */}
          <div className="flex items-center justify-between mb-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCalendarOffset((o) => o + 6)}
              disabled={!canGoBack}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Anterior
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCalendarOffset((o) => Math.max(0, o - 6))}
              disabled={!canGoForward}
            >
              Siguiente
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>

          {/* Matrix */}
          <div className="border rounded-lg bg-white overflow-x-auto">
            {calendarLoading ? (
              <div className="p-8 space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </div>
            ) : memberRows.length === 0 ? (
              <div className="text-center py-8 text-slate-500">No hay pagos</div>
            ) : (
              <table className="w-full text-sm border-collapse">
                <thead>
                  {/* Year row */}
                  <tr>
                    <th className="border-b border-r border-slate-200 px-3 py-2 text-left font-medium text-slate-500 bg-slate-50 w-48" />
                    {yearGroups.map((g) => (
                      <th
                        key={g.year}
                        colSpan={g.count}
                        className="border-b border-r border-slate-200 px-2 py-1.5 text-center font-semibold text-slate-700 bg-slate-50"
                      >
                        {g.year}
                      </th>
                    ))}
                  </tr>
                  {/* Month row */}
                  <tr>
                    <th className="border-b border-r border-slate-200 px-3 py-1.5 text-left text-xs font-medium text-slate-500 bg-slate-50">
                      Socio
                    </th>
                    {visibleMonths.map(({ month, year }) => (
                      <th
                        key={`${year}-${month}`}
                        className="border-b border-r border-slate-200 px-2 py-1.5 text-center text-xs font-medium text-slate-500 bg-slate-50 min-w-[48px]"
                      >
                        {MONTH_ABBR[month - 1]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {memberRows.map((row) => (
                    <tr key={row.membershipId} className="hover:bg-slate-50/50">
                      <td className="border-b border-r border-slate-200 px-3 py-1.5 font-medium text-slate-700 whitespace-nowrap">
                        {row.memberNumber !== null
                          ? `#${String(row.memberNumber).padStart(3, "0")} `
                          : ""}
                        {row.fullName}
                      </td>
                      {visibleMonths.map(({ month, year }) => {
                        const key = `${year}-${String(month).padStart(2, "0")}`;
                        const payment = row.paymentsByMonth.get(key);
                        const cls = cellClass(payment, row.unpaidStreak, key, row.startDate);
                        return (
                          <td
                            key={key}
                            className={`border-b border-r border-slate-200 text-center py-1.5 ${cls}`}
                          >
                            {payment?.status === "REJECTED" && (
                              <XCircle className="h-3.5 w-3.5 mx-auto" />
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Legend */}
          <div className="flex flex-wrap gap-3 mt-3 text-xs text-slate-600">
            {[
              { cls: "bg-green-100", label: "Confirmado" },
              { cls: "bg-amber-100", label: "Pendiente" },
              { cls: "bg-orange-100", label: "Sin pago (≤5 meses)" },
              { cls: "bg-red-200",   label: "Sin pago (>5 meses)" },
              { cls: "bg-red-100",   label: "Rechazado" },
              { cls: "bg-slate-100", label: "Reembolsado" },
            ].map(({ cls, label }) => (
              <span key={label} className="flex items-center gap-1.5">
                <span className={`inline-block w-3 h-3 rounded-sm ${cls}`} />
                {label}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
