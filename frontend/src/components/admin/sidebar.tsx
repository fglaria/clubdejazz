"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Users, CreditCard, Calendar } from "lucide-react";

const navItems = [
  { href: "/admin/members", label: "Socios", icon: Users },
  { href: "/admin/payments", label: "Pagos", icon: CreditCard },
  { href: "/admin/events", label: "Eventos", icon: Calendar },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 shrink-0 border-r bg-white h-screen sticky top-0">
      <div className="px-4 py-5 border-b">
        <h1 className="font-semibold text-sm text-slate-900">Club de Jazz</h1>
        <p className="text-xs text-slate-500">Intranet</p>
      </div>
      <nav className="p-2 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors",
              pathname.startsWith(href)
                ? "bg-slate-100 text-slate-900 font-medium"
                : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
