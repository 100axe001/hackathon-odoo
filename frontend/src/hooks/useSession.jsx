import { createContext, useContext, useEffect, useState } from "react";
import { loadSession, logout } from "@/api/api-functions/auth";

const SessionContext = createContext({ user: null, loading: true });

export function SessionProvider({ children }) {
  const [state, setState] = useState({ user: null, loading: true });

  useEffect(() => {
    let cancelled = false;
    loadSession().then((user) => {
      if (!cancelled) setState({ user, loading: false });
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = (user) => setState({ user, loading: false });

  // Clearing local state is not signing out: the cookie is httpOnly, so only
  // the server can invalidate it. Without this call the session survived and
  // typing /dashboard put you straight back in.
  const signOut = async () => {
    try {
      await logout();
    } finally {
      setState({ user: null, loading: false });
    }
  };

  return (
    <SessionContext.Provider value={{ ...state, signIn, signOut }}>
      {children}
    </SessionContext.Provider>
  );
}

export const useSession = () => useContext(SessionContext);
