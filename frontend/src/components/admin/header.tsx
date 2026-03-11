"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { removeToken } from "@/lib/auth";
import { LogOut } from "lucide-react";

export function Header({ title }: { title: string }) {
  const router = useRouter();

  function handleLogout() {
    removeToken();
    router.push("/login");
  }

  return (
    <header className="h-14 border-b bg-white flex items-center justify-between px-6">
      <h2 className="font-semibold text-slate-900">{title}</h2>
      <Button variant="ghost" size="sm" onClick={handleLogout}>
        <LogOut className="h-4 w-4 mr-2" />
        Salir
      </Button>
    </header>
  );
}
