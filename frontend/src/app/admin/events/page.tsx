"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { adminApi } from "@/lib/api";
import type { Event } from "@/lib/types";
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus, Pencil, Trash2, Eye, EyeOff } from "lucide-react";

interface EventForm {
  title: string;
  description: string;
  event_date: string;
  location: string;
  address: string;
  is_published: boolean;
}

export default function EventsPage() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingEvent, setEditingEvent] = useState<Event | null>(null);

  const { data: events, isLoading } = useQuery({
    queryKey: ["admin", "events"],
    queryFn: () => adminApi.events.list(true),
  });

  const form = useForm<EventForm>({
    defaultValues: {
      title: "",
      description: "",
      event_date: "",
      location: "",
      address: "",
      is_published: false,
    },
  });

  const createMutation = useMutation({
    mutationFn: (data: EventForm) => adminApi.events.create(data),
    onSuccess: () => {
      toast.success("Evento creado");
      queryClient.invalidateQueries({ queryKey: ["admin", "events"] });
      closeDialog();
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<EventForm> }) =>
      adminApi.events.update(id, data),
    onSuccess: () => {
      toast.success("Evento actualizado");
      queryClient.invalidateQueries({ queryKey: ["admin", "events"] });
      closeDialog();
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminApi.events.delete(id),
    onSuccess: () => {
      toast.success("Evento eliminado");
      queryClient.invalidateQueries({ queryKey: ["admin", "events"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const togglePublishMutation = useMutation({
    mutationFn: ({ id, is_published }: { id: string; is_published: boolean }) =>
      adminApi.events.update(id, { is_published }),
    onSuccess: (_, { is_published }) => {
      toast.success(is_published ? "Evento publicado" : "Evento despublicado");
      queryClient.invalidateQueries({ queryKey: ["admin", "events"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  function openCreate() {
    setEditingEvent(null);
    form.reset({
      title: "",
      description: "",
      event_date: "",
      location: "",
      address: "",
      is_published: false,
    });
    setDialogOpen(true);
  }

  function openEdit(event: Event) {
    setEditingEvent(event);
    form.reset({
      title: event.title,
      description: event.description || "",
      event_date: event.event_date.slice(0, 16),
      location: event.location || "",
      address: event.address || "",
      is_published: event.is_published,
    });
    setDialogOpen(true);
  }

  function closeDialog() {
    setDialogOpen(false);
    setEditingEvent(null);
    form.reset();
  }

  function onSubmit(data: EventForm) {
    if (editingEvent) {
      updateMutation.mutate({ id: editingEvent.id, data });
    } else {
      createMutation.mutate(data);
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Eventos</h1>
          <p className="text-sm text-slate-500">
            Gestiona los eventos del club
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4 mr-2" />
          Nuevo evento
        </Button>
      </div>

      <div className="border rounded-lg bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Titulo</TableHead>
              <TableHead>Fecha</TableHead>
              <TableHead>Lugar</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead className="text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell>
                    <Skeleton className="h-5 w-48" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-32" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-32" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-20" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-8 w-24 ml-auto" />
                  </TableCell>
                </TableRow>
              ))
            ) : events?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-slate-500">
                  No hay eventos
                </TableCell>
              </TableRow>
            ) : (
              events?.map((e: Event) => (
                <TableRow key={e.id}>
                  <TableCell className="font-medium">{e.title}</TableCell>
                  <TableCell>
                    {new Date(e.event_date).toLocaleString("es-CL", {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                  </TableCell>
                  <TableCell>{e.location || "-"}</TableCell>
                  <TableCell>
                    <Badge
                      variant="secondary"
                      className={
                        e.is_published
                          ? "bg-green-100 text-green-800"
                          : "bg-slate-100 text-slate-800"
                      }
                    >
                      {e.is_published ? "Publicado" : "Borrador"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() =>
                          togglePublishMutation.mutate({
                            id: e.id,
                            is_published: !e.is_published,
                          })
                        }
                        disabled={togglePublishMutation.isPending}
                      >
                        {e.is_published ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => openEdit(e)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        onClick={() => {
                          if (confirm("Eliminar este evento?")) {
                            deleteMutation.mutate(e.id);
                          }
                        }}
                        disabled={deleteMutation.isPending}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingEvent ? "Editar evento" : "Nuevo evento"}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title">Titulo</Label>
              <Input id="title" {...form.register("title", { required: true })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="event_date">Fecha y hora</Label>
              <Input
                id="event_date"
                type="datetime-local"
                {...form.register("event_date", { required: true })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="location">Lugar</Label>
              <Input id="location" {...form.register("location")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="address">Direccion</Label>
              <Input id="address" {...form.register("address")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Descripcion</Label>
              <Input id="description" {...form.register("description")} />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_published"
                {...form.register("is_published")}
                className="h-4 w-4"
              />
              <Label htmlFor="is_published" className="font-normal">
                Publicar inmediatamente
              </Label>
            </div>
            <div className="flex justify-end gap-2 pt-4">
              <Button type="button" variant="outline" onClick={closeDialog}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending ? "Guardando..." : "Guardar"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
