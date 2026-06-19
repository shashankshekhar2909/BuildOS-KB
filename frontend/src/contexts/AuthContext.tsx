"use client";
import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { loginWithGoogle, logoutFirebase } from "@/lib/firebase";

function getBase(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined") {
    const { protocol, hostname, port } = window.location;
    if (protocol === "https:" || !port || port === "80" || port === "443") {
      return `${protocol}//${hostname}`;
    }
    return `${protocol}//${hostname}:8010`;
  }
  return "http://localhost:8010";
}
const TOKEN_KEY = "buildos_access_token";

export interface AuthUser {
  id: string;
  email: string;
  display_name: string | null;
  role: "admin" | "viewer";
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  getToken: () => string | null;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const getToken = useCallback((): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(TOKEN_KEY);
  }, []);

  const fetchMe = useCallback(async (token: string): Promise<AuthUser | null> => {
    try {
      const res = await fetch(`${getBase()}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return null;
      return res.json();
    } catch {
      return null;
    }
  }, []);

  // Restore session from localStorage on mount
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    fetchMe(token).then((u) => {
      setUser(u);
      if (!u) localStorage.removeItem(TOKEN_KEY);
      setLoading(false);
    });
  }, [getToken, fetchMe]);

  const login = useCallback(async () => {
    const firebaseToken = await loginWithGoogle();
    const res = await fetch(`${getBase()}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ firebase_token: firebaseToken }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? "Login failed");
    }
    const data = await res.json();
    localStorage.setItem(TOKEN_KEY, data.access_token);
    setUser(data.user);
  }, []);

  const logout = useCallback(async () => {
    await logoutFirebase();
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, getToken }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
