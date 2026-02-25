"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { supabase } from "./supabase";
import { setAuthToken } from "./auth-token";
import type { Session, User } from "@supabase/supabase-js";

interface AuthContextValue {
  session: Session | null;
  user: User | null;
  role: string;
  loading: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  session: null,
  user: null,
  role: "viewer",
  loading: true,
  signOut: async () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(!!supabase);
  const prevTokenRef = useRef<string | null>(null);

  useEffect(() => {
    if (!supabase) return;

    supabase.auth.getSession().then(({ data }) => {
      const s = data.session;
      setSession(s);
      setAuthToken(s?.access_token ?? null);
      prevTokenRef.current = s?.access_token ?? null;
      setLoading(false);
    }).catch(() => {
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, newSession) => {
      const newToken = newSession?.access_token ?? null;
      if (newToken !== prevTokenRef.current) {
        prevTokenRef.current = newToken;
        setSession(newSession);
        setAuthToken(newToken);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const user = session?.user ?? null;
  const role =
    (typeof user?.app_metadata?.role === "string"
      ? user.app_metadata.role
      : null) ?? "viewer";

  async function signOut() {
    if (!supabase) return;
    await supabase.auth.signOut();
    setSession(null);
    setAuthToken(null);
  }

  return (
    <AuthContext.Provider value={{ session, user, role, loading, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}
