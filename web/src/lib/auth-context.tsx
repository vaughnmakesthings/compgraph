"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
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

/** Check URL hash for Supabase invite/recovery tokens */
function getHashType(): string | null {
  if (typeof window === "undefined") return null;
  const hash = window.location.hash.substring(1);
  const params = new URLSearchParams(hash);
  return params.get("type");
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(!!supabase);
  const prevTokenRef = useRef<string | null>(null);
  const redirectedRef = useRef(false);

  useEffect(() => {
    if (!supabase) return;

    let mounted = true;

    // Detect invite/recovery tokens in URL hash before Supabase consumes them
    const hashType = getHashType();

    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      const s = data.session;
      setSession(s);
      setAuthToken(s?.access_token ?? null);
      prevTokenRef.current = s?.access_token ?? null;
      setLoading(false);
    }).catch(() => {
      if (mounted) setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, newSession) => {
      const newToken = newSession?.access_token ?? null;
      if (newToken !== prevTokenRef.current || event === "USER_UPDATED") {
        prevTokenRef.current = newToken;
        setSession(newSession);
        setAuthToken(newToken);
      }

      // Redirect invite/recovery users to /setup after session is established
      if (
        newSession &&
        !redirectedRef.current &&
        (hashType === "invite" || hashType === "recovery")
      ) {
        redirectedRef.current = true;
        const email = newSession.user?.email ?? "";
        router.replace(`/setup?email=${encodeURIComponent(email)}`);
      }
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [router]);

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
