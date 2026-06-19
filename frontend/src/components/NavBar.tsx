"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/projects", label: "Projects" },
  { href: "/search", label: "Search" },
];

export function NavBar() {
  const pathname = usePathname();

  if (pathname === "/") return null;

  return (
    <nav className="sticky top-0 z-50 flex items-center h-12 px-6 gap-6 border-b border-border bg-surface/95 backdrop-blur-sm">
      <Link href="/" className="font-bold text-text text-sm no-underline hover:text-accent transition-colors">
        BuildOS KB
      </Link>

      <div className="flex items-center gap-1">
        {NAV_LINKS.map(({ href, label }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`px-3 py-1 text-sm no-underline rounded transition-colors ${
                active
                  ? "text-text bg-surface-2"
                  : "text-muted hover:text-text hover:bg-surface-2"
              }`}
            >
              {label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
