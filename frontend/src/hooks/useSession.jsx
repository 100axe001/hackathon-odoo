import { createContext, useContext, useEffect, useState } from "react";
import { loadSession } from "@/api/api-functions/auth";

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
  const signOut = () => setState({ user: null, loading: false });

  return (
    <SessionContext.Provider value={{ ...state, signIn, signOut }}>
      {children}
    </SessionContext.Provider>
  );
}

export const useSession = () => useContext(SessionContext);
