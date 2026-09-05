import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { LogoMarkLight } from "@/components/layout/LogoMark";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { C } from "@/constants/theme";
import { login, signup } from "@/api/api-functions/auth";
import { useSession } from "@/hooks/useSession";

export function LoginScreen() {
  const navigate = useNavigate();
  const { signIn } = useSession();
  const [tab, setTab] = useState("Log In");
  const [email, setEmail] = useState("rep@dealflow360.com");
  const [password, setPassword] = useState("dealflow123");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user =
        tab === "Log In"
          ? await login(email, password)
          : await signup(email, password, fullName);
      signIn(user);
      // A customer has no internal screens, so send them to their portal.
      navigate(user.role === "CUSTOMER" ? "/portal" : "/dashboard");
    } catch {
      // client.js throws on a non-2xx, so this covers wrong credentials, a
      // duplicate email, and the API being down.
      setError(
        tab === "Log In"
          ? "Incorrect email or password."
          : "Could not create that account. The email may already be in use.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{ backgroundColor: C.bg }}
    >
      <div
        className="w-full flex flex-col items-center"
        style={{ maxWidth: 420 }}
      >
        <div className="mb-6">
          <LogoMarkLight />
        </div>
        <Card className="w-full">
          <div
            className="flex gap-6 mb-5"
            style={{ borderBottom: `1px solid ${C.border}` }}
          >
            {["Log In", "Sign Up"].map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className="text-sm pb-3 transition-colors duration-150"
                style={{
                  color: tab === t ? C.accent : C.muted,
                  borderBottom:
                    tab === t
                      ? `2px solid ${C.accent}`
                      : "2px solid transparent",
                  fontWeight: tab === t ? 500 : 400,
                }}
              >
                {t}
              </button>
            ))}
          </div>
          <form onSubmit={submit} className="flex flex-col gap-4">
            <div>
              <label className="text-sm mb-1 block" style={{ color: C.text }}>
                Email
              </label>
              <Input
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            {tab === "Sign Up" && (
              <div>
                <label className="text-sm mb-1 block" style={{ color: C.text }}>
                  Full name
                </label>
                <Input
                  placeholder="Alex Turner"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>
            )}
            <div>
              <label className="text-sm mb-1 block" style={{ color: C.text }}>
                Password
              </label>
              <Input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {tab === "Log In" && (
              <button
                type="button"
                onClick={() =>
                  setError(
                    "Password reset is not part of this build - ask an admin to reset it.",
                  )
                }
                className="text-sm text-left"
                style={{ color: C.muted }}
              >
                Forgot password?
              </button>
            )}
            {error && (
              <div
                className="text-sm rounded-md px-3 py-2"
                style={{ color: C.dangerText, backgroundColor: C.dangerBg }}
              >
                {error}
              </div>
            )}
            <Button variant="primary" type="submit" className="w-full mt-2">
              {busy ? "…" : tab === "Log In" ? "Log In" : "Create Account"}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
