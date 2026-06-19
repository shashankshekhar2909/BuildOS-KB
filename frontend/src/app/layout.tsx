import type { Metadata } from "next";
import { Providers } from "@/lib/providers";
import { AuthProvider } from "@/contexts/AuthContext";
import { AuthGuard } from "@/components/AuthGuard";
import { NavBar } from "@/components/NavBar";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "BuildOS Knowledge Hub",
    template: "%s | BuildOS KB",
  },
  description: "Self-hosted AI memory for your projects. Auto-indexes every codebase, generates OKF files, exposes search + MCP tools.",
  authors: [{ name: "Shashank Shekhar" }],
  creator: "BuildWithShashank",
  publisher: "BuildWithShashank",
  keywords: ["AI memory", "knowledge base", "MCP", "code search", "BuildWithShashank", "self-hosted"],
  openGraph: {
    type: "website",
    title: "BuildOS Knowledge Hub",
    description: "Self-hosted AI memory for your projects.",
    siteName: "BuildOS KB",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <AuthProvider>
            <AuthGuard>
              <NavBar />
              {children}
            </AuthGuard>
          </AuthProvider>
        </Providers>
      </body>
    </html>
  );
}
