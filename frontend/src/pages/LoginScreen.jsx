import { useState } from "react";
import { LogoMarkLight } from "@/components/layout/LogoMark";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { C } from "@/constants/theme";

export function LoginScreen({ setRoute }) {
  const [tab, setTab] = useState("Log In");
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
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setRoute({ name: "dashboard", id: null });
            }}
            className="flex flex-col gap-4"
          >
            <div>
              <label className="text-sm mb-1 block" style={{ color: C.text }}>
                Email
              </label>
              <Input type="email" placeholder="you@company.com" />
            </div>
            <div>
              <label className="text-sm mb-1 block" style={{ color: C.text }}>
                Password
              </label>
              <Input type="password" placeholder="••••••••" />
            </div>
            {tab === "Log In" && (
              <button
                type="button"
                className="text-sm text-left"
                style={{ color: C.muted }}
              >
                Forgot password?
              </button>
            )}
            <Button variant="primary" type="submit" className="w-full mt-2">
              {tab === "Log In" ? "Log In" : "Create Account"}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
