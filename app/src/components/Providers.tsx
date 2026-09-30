"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api, call, getToken, raw, setToken } from "@/lib/api";

import { ToastProvider } from "./Toast";

export interface Me {
  user_id: string;
  email: string;
  role: string;
  display_name?: string | null;
  email_notifications: boolean;
}

interface AuthState {
  me: Me | null;
  ready: boolean;
  pendingConsent: number;
  refreshPending(): Promise<void>;
  login(email: string, password: string): Promise<void>;
  register(email: string, password: string): Promise<void>;
  logout(): void;
  refresh(): Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside Providers");
  return ctx;
}

function ServiceWorker() {
  useEffect(() => {
    if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") {
      navigator.serviceWorker.register("/sw.js").catch(() => undefined);
    }
  }, []);
  return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [ready, setReady] = useState(false);
  const [pendingConsent, setPending] = useState(0);

  const refreshPending = useCallback(async () => {
    if (!getToken()) return setPending(0);
    try {
      const inbox = await raw<{ pending: number }>("/consent/inbox?status=pending");
      setPending(inbox.pending);
    } catch {
      /* keep the last known count */
    }
  }, []);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setMe(null);
      setReady(true);
      return;
    }
    try {
      setMe((await call(api.GET("/auth/me"))) as Me);
    } catch (e) {
      if ((e as { status?: number }).status === 401) setToken(null);
      setMe(null);
    } finally {
      setReady(true);
    }
  }, []);

  useEffect(() => {
    // Initial session check against the backend on mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!me) return;
    // Keep the Consent tab badge fresh while signed in.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshPending();
    const timer = window.setInterval(() => void refreshPending(), 30000);
    return () => window.clearInterval(timer);
  }, [me, refreshPending]);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await call(api.POST("/auth/login", { body: { email, password } }));
      setToken(res.access_token);
      await refresh();
    },
    [refresh],
  );

  const register = useCallback(
    async (email: string, password: string) => {
      await call(api.POST("/auth/register", { body: { email, password } }));
      await login(email, password);
    },
    [login],
  );

  const logout = useCallback(() => {
    setToken(null);
    setMe(null);
    setPending(0);
  }, []);

  const value = useMemo(
    () => ({ me, ready, pendingConsent, refreshPending, login, register, logout, refresh }),
    [me, ready, pendingConsent, refreshPending, login, register, logout, refresh],
  );

  return (
    <AuthContext.Provider value={value}>
      <ToastProvider>
        <ServiceWorker />
        {children}
      </ToastProvider>
    </AuthContext.Provider>
  );
}

/** Wrap pages that need an account; sends visitors to the sign-in screen. */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { me, ready } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (ready && !me) router.replace("/masuk/");
  }, [ready, me, router]);
  if (!ready || !me) {
    return (
      <p role="status" style={{ padding: 24, color: "var(--muted)" }}>
        Memuat...
      </p>
    );
  }
  return <>{children}</>;
}
