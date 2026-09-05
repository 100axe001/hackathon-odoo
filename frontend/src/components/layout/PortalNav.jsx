import { LogoMarkLight } from "@/components/layout/LogoMark";
import { C } from "@/constants/theme";

export function PortalNav({ portalTab, setPortalTab }) {
  const items = ["My Quotation", "Messages", "Profile"];
  return (
    <div
      className="bg-white border-b sticky top-0 z-10"
      style={{ borderColor: C.border }}
    >
      <div className="max-w-[1000px] mx-auto flex items-center justify-between px-8 py-4">
        <LogoMarkLight />
        <div className="flex items-center gap-8">
          {items.map((item) => (
            <button
              key={item}
              onClick={() => setPortalTab(item)}
              className="text-sm pb-1 transition-colors duration-150"
              style={{
                color: portalTab === item ? C.accent : C.muted,
                borderBottom:
                  portalTab === item
                    ? `2px solid ${C.accent}`
                    : "2px solid transparent",
                fontWeight: portalTab === item ? 500 : 400,
              }}
            >
              {item}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
