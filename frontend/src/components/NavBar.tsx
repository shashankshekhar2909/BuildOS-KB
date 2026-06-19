"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/projects", label: "Projects" },
  { href: "/search", label: "Search" },
];

export function NavBar() {
  const pathname = usePathname();
  const { user, loading, login, logout } = useAuth();

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

      <div className="ml-auto flex items-center gap-3">
        {loading ? (
          <span className="text-xs text-subtle animate-pulse">…</span>
        ) : user ? (
          <>
            <span className="text-xs text-muted hidden sm:block truncate max-w-[160px]">{user.email}</span>
            <button
              onClick={() => logout()}
              className="text-xs text-subtle bg-transparent border-0 cursor-pointer hover:text-text transition-colors"
            >
              Sign out
            </button>
          </>
        ) : (
          <button
            onClick={() => login()}
            className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold text-white bg-accent hover:opacity-90 transition-opacity border-0 cursor-pointer"
          >
            <GoogleIcon />
            Sign in
          </button>
        )}
      </div>
    </nav>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" width="12" height="12" xmlns="http://www.w3.org/2000/svg">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  );
}
