"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { adminApi } from "@/lib/api";
import type { Membership, MembershipStatus, RoleAssignment, UserProfileUpdate } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle, XCircle, KeyRound, Pencil, Shield, UserPlus, ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react";

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

const membershipTypeOptions = [
  { code: "NUMERARIO", label: "Numerario" },
  { code: "HONORARIO", label: "Honorario" },
  { code: "FUNDADOR", label: "Fundador" },
  { code: "ESTUDIANTE", label: "Estudiante" },
];

const filterLabels: Record<MembershipStatus | "ALL", string> = {
  ALL: "Todos",
  PENDING: "Pendientes",
  ACTIVE: "Activos",
  SUSPENDED: "Suspendidos",
  EXPIRED: "Expirados",
  CANCELLED: "Cancelados",
};

const emptyForm = {
  first_name: "",
  middle_name: "",
  last_name_1: "",
  last_name_2: "",
  email: "",
  rut: "",
  phone: "",
  password: "",
  membership_type_code: "NUMERARIO",
};

const emptyEditForm: UserProfileUpdate & { is_active: boolean } = {
  first_name: "",
  middle_name: "",
  last_name_1: "",
  last_name_2: "",
  email: "",
  rut: "",
  phone: "",
  is_active: true,
};

const ALL_ROLES = ["MEMBER", "ADMIN", "SUPER_ADMIN"] as const;

const roleBadgeColors: Record<string, string> = {
  MEMBER: "bg-slate-100 text-slate-600",
  ADMIN: "bg-blue-100 text-blue-800",
  SUPER_ADMIN: "bg-red-100 text-red-800",
};

export default function MembersPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<MembershipStatus | "ALL">("ALL");
  const [sort, setSort] = useState<{ col: string; dir: "asc" | "desc" }>({ col: "member_number", dir: "asc" });

  // Create member dialog state
  const [newMemberOpen, setNewMemberOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);

  // Reset password dialog state
  const [resetTarget, setResetTarget] = useState<{ id: string; name: string } | null>(null);
  const [newPassword, setNewPassword] = useState("");

  // Assign membership dialog state
  const [assignOpen, setAssignOpen] = useState(false);
  const [assignForm, setAssignForm] = useState({ user_id: "", membership_type_code: "NUMERARIO" });

  // Role management dialog state
  const [rolesTarget, setRolesTarget] = useState<{ id: string; name: string } | null>(null);

  // Edit user dialog state
  const [editTarget, setEditTarget] = useState<{ id: string; name: string } | null>(null);
  const [editForm, setEditForm] = useState<UserProfileUpdate & { is_active: boolean }>(emptyEditForm);

  const { data: memberships, isLoading } = useQuery({
    queryKey: ["admin", "memberships", statusFilter],
    queryFn: () =>
      adminApi.memberships.list(statusFilter === "ALL" ? undefined : statusFilter),
  });

  const { data: pendingCount } = useQuery({
    queryKey: ["admin", "memberships", "pendingCount"],
    queryFn: () => adminApi.memberships.pendingCount(),
  });

  const { data: usersWithoutMembership } = useQuery({
    queryKey: ["admin", "users", "withoutMembership"],
    queryFn: () => adminApi.users.withoutMembership(),
    enabled: assignOpen,
  });

  const { data: targetRoles, isLoading: rolesLoading } = useQuery({
    queryKey: ["admin", "users", rolesTarget?.id, "roles"],
    queryFn: () => adminApi.users.getRoles(rolesTarget!.id),
    enabled: rolesTarget !== null,
  });

  const { data: editUserData, isLoading: editUserLoading } = useQuery({
    queryKey: ["admin", "users", editTarget?.id],
    queryFn: () => adminApi.users.get(editTarget!.id),
    enabled: editTarget !== null,
  });

  // Sync fetched user data into the edit form
  useEffect(() => {
    if (editUserData) {
      setEditForm({
        first_name: editUserData.first_name,
        middle_name: editUserData.middle_name ?? "",
        last_name_1: editUserData.last_name_1,
        last_name_2: editUserData.last_name_2 ?? "",
        email: editUserData.email,
        rut: editUserData.rut ?? "",
        phone: editUserData.phone ?? "",
        is_active: editUserData.is_active,
      });
    }
  }, [editUserData]);

  const reviewMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "approve" | "reject" }) =>
      adminApi.memberships.review(id, action),
    onSuccess: (_, { action }) => {
      toast.success(action === "approve" ? "Solicitud aprobada" : "Solicitud rechazada");
      queryClient.invalidateQueries({ queryKey: ["admin", "memberships"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      adminApi.members.create({
        ...form,
        middle_name: form.middle_name || undefined,
        last_name_2: form.last_name_2 || undefined,
        phone: form.phone || undefined,
      }),
    onSuccess: () => {
      toast.success("Socio creado");
      queryClient.invalidateQueries({ queryKey: ["admin", "memberships"] });
      setNewMemberOpen(false);
      setForm(emptyForm);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const resetPasswordMutation = useMutation({
    mutationFn: () => adminApi.users.resetPassword(resetTarget!.id, newPassword),
    onSuccess: () => {
      toast.success("Contraseña actualizada");
      setResetTarget(null);
      setNewPassword("");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const setRoleMutation = useMutation({
    mutationFn: ({ role_name, user_id }: { role_name: string; user_id: string }) =>
      adminApi.users.setRole(user_id, role_name),
    onSuccess: (_, { role_name, user_id }) => {
      toast.success(`Rol cambiado a ${role_name}`);
      queryClient.invalidateQueries({ queryKey: ["admin", "memberships"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "users", user_id, "roles"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const assignMutation = useMutation({
    mutationFn: () =>
      adminApi.memberships.assign({
        user_id: assignForm.user_id,
        membership_type_code: assignForm.membership_type_code,
      }),
    onSuccess: () => {
      toast.success("Membresía asignada");
      queryClient.invalidateQueries({ queryKey: ["admin", "memberships"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "users", "withoutMembership"] });
      setAssignOpen(false);
      setAssignForm({ user_id: "", membership_type_code: "NUMERARIO" });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const updateUserMutation = useMutation({
    mutationFn: () => adminApi.users.update(editTarget!.id, {
      first_name: editForm.first_name || undefined,
      middle_name: editForm.middle_name || undefined,
      last_name_1: editForm.last_name_1 || undefined,
      last_name_2: editForm.last_name_2 || undefined,
      email: editForm.email || undefined,
      rut: editForm.rut || undefined,
      phone: editForm.phone || undefined,
      is_active: editForm.is_active,
    }),
    onSuccess: () => {
      toast.success("Datos actualizados");
      queryClient.invalidateQueries({ queryKey: ["admin", "memberships"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "users", editTarget?.id] });
      setEditTarget(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const toggleSort = (col: string) =>
    setSort((s) => s.col === col ? { col, dir: s.dir === "asc" ? "desc" : "asc" } : { col, dir: "asc" });

  const SortIcon = ({ col }: { col: string }) => {
    if (sort.col !== col) return <ChevronsUpDown className="h-3 w-3 ml-1 text-slate-400" />;
    return sort.dir === "asc"
      ? <ChevronUp className="h-3 w-3 ml-1" />
      : <ChevronDown className="h-3 w-3 ml-1" />;
  };

  const sorted = [...(memberships ?? [])].sort((a, b) => {
    const dir = sort.dir === "asc" ? 1 : -1;
    switch (sort.col) {
      case "member_number": {
        const an = a.user.member_number ?? Infinity;
        const bn = b.user.member_number ?? Infinity;
        return (an - bn) * dir;
      }
      case "name":
        return a.user.full_name.localeCompare(b.user.full_name, "es") * dir;
      case "email":
        return a.user.email.localeCompare(b.user.email, "es") * dir;
      case "type":
        return a.membership_type.name.localeCompare(b.membership_type.name, "es") * dir;
      case "status":
        return a.status.localeCompare(b.status) * dir;
      case "start_date":
        return (a.start_date > b.start_date ? 1 : -1) * dir;
      default:
        return 0;
    }
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
        <div className="flex items-center gap-2">
          <Select
            value={statusFilter}
            onValueChange={(v) => setStatusFilter(v as MembershipStatus | "ALL")}
          >
            <SelectTrigger className="w-40">
              <SelectValue>{filterLabels[statusFilter]}</SelectValue>
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
          <Button size="sm" variant="outline" onClick={() => setAssignOpen(true)}>
            Asignar Membresía
          </Button>
          <Button size="sm" onClick={() => setNewMemberOpen(true)}>
            <UserPlus className="h-4 w-4 mr-1" />
            Nuevo Socio
          </Button>
        </div>
      </div>

      <div className="border rounded-lg bg-white">
        <Table className="w-full [&_th]:px-2 [&_td]:px-2">
          <TableHeader>
            <TableRow>
              {[
                { col: "member_number", label: "#", className: "w-10 cursor-pointer select-none" },
                { col: "name", label: "Nombre", className: "cursor-pointer select-none" },
                { col: "email", label: "Correo", className: "cursor-pointer select-none" },
                { col: "phone", label: "Teléfono", className: "w-28 select-none" },
                { col: "type", label: "Tipo", className: "w-32 cursor-pointer select-none" },
                { col: "roles", label: "Rol", className: "w-20 select-none" },
                { col: "status", label: "Estado", className: "w-24 cursor-pointer select-none" },
                { col: "start_date", label: "Inicio", className: "w-24 cursor-pointer select-none" },
              ].map(({ col, label, className }) => (
                <TableHead key={col} className={className} onClick={() => toggleSort(col)}>
                  <span className="inline-flex items-center">{label}<SortIcon col={col} /></span>
                </TableHead>
              ))}
              <TableHead className="text-right w-24">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell><Skeleton className="h-5 w-8" /></TableCell>
                  <TableCell><Skeleton className="h-5 w-40" /></TableCell>
                  <TableCell><Skeleton className="h-5 w-40" /></TableCell>
                  <TableCell><Skeleton className="h-5 w-28" /></TableCell>
                  <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                  <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                  <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                  <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                  <TableCell><Skeleton className="h-8 w-16 ml-auto" /></TableCell>
                </TableRow>
              ))
            ) : memberships?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8 text-slate-500">
                  No hay membresías
                </TableCell>
              </TableRow>
            ) : (
              sorted.map((m: Membership) => (
                <TableRow key={m.id}>
                  <TableCell className="text-slate-400 text-sm">
                    {m.user.member_number ?? "—"}
                  </TableCell>
                  <TableCell className="font-medium">{m.user.full_name}</TableCell>
                  <TableCell className="text-slate-500">{m.user.email}</TableCell>
                  <TableCell className="text-slate-500">{m.user.phone ?? "—"}</TableCell>
                  <TableCell>{m.membership_type.name}</TableCell>
                  <TableCell>
                    {(m.user.roles ?? []).length === 0 ? (
                      <span className="text-slate-400 text-sm">—</span>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {(m.user.roles ?? []).map((r) => (
                          <Badge
                            key={r}
                            variant="secondary"
                            className={roleBadgeColors[r] ?? "bg-slate-100 text-slate-700"}
                          >
                            {r}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className={statusColors[m.status]}>
                      {statusLabels[m.status]}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {new Date(m.start_date).toLocaleDateString("es-CL")}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-slate-500 hover:text-slate-700"
                        onClick={() => setEditTarget({ id: m.user_id, name: m.user.full_name })}
                        title="Editar usuario"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      {m.status === "PENDING" && (
                        <>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-green-600 hover:text-green-700 hover:bg-green-50"
                            onClick={() => reviewMutation.mutate({ id: m.id, action: "approve" })}
                            disabled={reviewMutation.isPending}
                          >
                            <CheckCircle className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            onClick={() => reviewMutation.mutate({ id: m.id, action: "reject" })}
                            disabled={reviewMutation.isPending}
                          >
                            <XCircle className="h-4 w-4" />
                          </Button>
                        </>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-slate-500 hover:text-slate-700"
                        onClick={() => setResetTarget({ id: m.user_id, name: m.user.full_name })}
                        title="Resetear contraseña"
                      >
                        <KeyRound className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-slate-500 hover:text-slate-700"
                        onClick={() => setRolesTarget({ id: m.user_id, name: m.user.full_name })}
                        title="Gestionar roles"
                      >
                        <Shield className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Create member dialog */}
      <Dialog
        open={newMemberOpen}
        onOpenChange={(open) => {
          setNewMemberOpen(open);
          if (!open) setForm(emptyForm);
        }}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Nuevo Socio</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-4 py-2">
            <div className="space-y-1">
              <Label>Nombre *</Label>
              <Input
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                placeholder="Juan"
              />
            </div>
            <div className="space-y-1">
              <Label>Segundo nombre</Label>
              <Input
                value={form.middle_name}
                onChange={(e) => setForm({ ...form, middle_name: e.target.value })}
                placeholder="Carlos"
              />
            </div>
            <div className="space-y-1">
              <Label>Apellido paterno *</Label>
              <Input
                value={form.last_name_1}
                onChange={(e) => setForm({ ...form, last_name_1: e.target.value })}
                placeholder="Pérez"
              />
            </div>
            <div className="space-y-1">
              <Label>Apellido materno</Label>
              <Input
                value={form.last_name_2}
                onChange={(e) => setForm({ ...form, last_name_2: e.target.value })}
                placeholder="González"
              />
            </div>
            <div className="space-y-1 col-span-2">
              <Label>Email *</Label>
              <Input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="juan@ejemplo.cl"
              />
            </div>
            <div className="space-y-1">
              <Label>RUT *</Label>
              <Input
                value={form.rut}
                onChange={(e) => setForm({ ...form, rut: e.target.value })}
                placeholder="12345678-9"
              />
            </div>
            <div className="space-y-1">
              <Label>Teléfono</Label>
              <Input
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                placeholder="+56912345678"
              />
            </div>
            <div className="space-y-1">
              <Label>Contraseña *</Label>
              <Input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="Mínimo 8 caracteres"
              />
            </div>
            <div className="space-y-1">
              <Label>Tipo de membresía *</Label>
              <Select
                value={form.membership_type_code}
                onValueChange={(v) => setForm({ ...form, membership_type_code: v ?? form.membership_type_code })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {membershipTypeOptions.map((t) => (
                    <SelectItem key={t.code} value={t.code}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setNewMemberOpen(false); setForm(emptyForm); }}>
              Cancelar
            </Button>
            <Button
              onClick={() => createMutation.mutate()}
              disabled={
                createMutation.isPending ||
                !form.first_name ||
                !form.last_name_1 ||
                !form.email ||
                !form.rut ||
                form.password.length < 8
              }
            >
              {createMutation.isPending ? "Creando..." : "Crear socio"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset password dialog */}
      <Dialog
        open={resetTarget !== null}
        onOpenChange={(open) => {
          if (!open) { setResetTarget(null); setNewPassword(""); }
        }}
      >
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Resetear contraseña</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-slate-500">{resetTarget?.name}</p>
          <div className="space-y-1 py-2">
            <Label>Nueva contraseña</Label>
            <Input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Mínimo 8 caracteres"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setResetTarget(null); setNewPassword(""); }}>
              Cancelar
            </Button>
            <Button
              onClick={() => resetPasswordMutation.mutate()}
              disabled={resetPasswordMutation.isPending || newPassword.length < 8}
            >
              {resetPasswordMutation.isPending ? "Guardando..." : "Guardar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Assign membership dialog */}
      <Dialog
        open={assignOpen}
        onOpenChange={(open) => {
          setAssignOpen(open);
          if (!open) setAssignForm({ user_id: "", membership_type_code: "NUMERARIO" });
        }}
      >
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Asignar Membresía</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1">
              <Label>Usuario</Label>
              <Select
                value={assignForm.user_id}
                onValueChange={(v) => setAssignForm({ ...assignForm, user_id: v ?? assignForm.user_id })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar usuario..." />
                </SelectTrigger>
                <SelectContent>
                  {usersWithoutMembership?.map((u) => (
                    <SelectItem key={u.id} value={u.id}>
                      {u.full_name} ({u.email})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Tipo de membresía</Label>
              <Select
                value={assignForm.membership_type_code}
                onValueChange={(v) => setAssignForm({ ...assignForm, membership_type_code: v ?? assignForm.membership_type_code })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {membershipTypeOptions.map((t) => (
                    <SelectItem key={t.code} value={t.code}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setAssignOpen(false);
                setAssignForm({ user_id: "", membership_type_code: "NUMERARIO" });
              }}
            >
              Cancelar
            </Button>
            <Button
              onClick={() => assignMutation.mutate()}
              disabled={assignMutation.isPending || !assignForm.user_id}
            >
              {assignMutation.isPending ? "Asignando..." : "Asignar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {/* Edit user dialog */}
      <Dialog
        open={editTarget !== null}
        onOpenChange={(open) => {
          if (!open) { setEditTarget(null); setEditForm(emptyEditForm); }
        }}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Editar socio</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-slate-500">{editTarget?.name}</p>
          {editUserLoading ? (
            <div className="grid grid-cols-2 gap-4 py-2">
              {Array.from({ length: 7 }).map((_, i) => (
                <div key={i} className="space-y-1">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-9 w-full" />
                </div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4 py-2">
              <div className="space-y-1">
                <Label>Nombre *</Label>
                <Input
                  value={editForm.first_name}
                  onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })}
                />
              </div>
              <div className="space-y-1">
                <Label>Segundo nombre</Label>
                <Input
                  value={editForm.middle_name}
                  onChange={(e) => setEditForm({ ...editForm, middle_name: e.target.value })}
                />
              </div>
              <div className="space-y-1">
                <Label>Apellido paterno *</Label>
                <Input
                  value={editForm.last_name_1}
                  onChange={(e) => setEditForm({ ...editForm, last_name_1: e.target.value })}
                />
              </div>
              <div className="space-y-1">
                <Label>Apellido materno</Label>
                <Input
                  value={editForm.last_name_2}
                  onChange={(e) => setEditForm({ ...editForm, last_name_2: e.target.value })}
                />
              </div>
              <div className="space-y-1 col-span-2">
                <Label>Email *</Label>
                <Input
                  type="email"
                  value={editForm.email}
                  onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                />
              </div>
              <div className="space-y-1">
                <Label>RUT</Label>
                <Input
                  value={editForm.rut}
                  onChange={(e) => setEditForm({ ...editForm, rut: e.target.value })}
                />
              </div>
              <div className="space-y-1">
                <Label>Teléfono</Label>
                <Input
                  value={editForm.phone}
                  onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                />
              </div>
              <div className="col-span-2 flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="edit-is-active"
                  checked={editForm.is_active}
                  onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                  className="h-4 w-4"
                />
                <Label htmlFor="edit-is-active">Usuario activo</Label>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => { setEditTarget(null); setEditForm(emptyEditForm); }}>
              Cancelar
            </Button>
            <Button
              onClick={() => updateUserMutation.mutate()}
              disabled={
                updateUserMutation.isPending ||
                editUserLoading ||
                !editForm.first_name ||
                !editForm.last_name_1 ||
                !editForm.email
              }
            >
              {updateUserMutation.isPending ? "Guardando..." : "Guardar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Role management dialog */}
      <Dialog
        open={rolesTarget !== null}
        onOpenChange={(open) => {
          if (!open) setRolesTarget(null);
        }}
      >
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Gestionar roles</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-slate-500">{rolesTarget?.name}</p>
          <div className="space-y-2 py-2">
            {rolesLoading ? (
              <p className="text-sm text-slate-400">Cargando...</p>
            ) : (
              ALL_ROLES.map((roleName) => {
                const isCurrent = (targetRoles ?? []).some((r: RoleAssignment) => r.name === roleName);
                return (
                  <div key={roleName} className="flex items-center justify-between py-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{roleName}</span>
                      {isCurrent && (
                        <Badge variant="secondary" className={roleBadgeColors[roleName] ?? "bg-slate-100 text-slate-700"}>
                          actual
                        </Badge>
                      )}
                    </div>
                    <Button
                      size="sm"
                      variant={isCurrent ? "secondary" : "outline"}
                      className="w-24"
                      disabled={isCurrent || setRoleMutation.isPending}
                      onClick={() =>
                        setRoleMutation.mutate({
                          role_name: roleName,
                          user_id: rolesTarget!.id,
                        })
                      }
                    >
                      {isCurrent ? "Asignado" : "Establecer"}
                    </Button>
                  </div>
                );
              })
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRolesTarget(null)}>
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
