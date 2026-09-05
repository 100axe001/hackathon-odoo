import { LogoMark } from "@/components/layout/LogoMark";
import { NAV_ITEMS } from "@/constants/nav";
import { C } from "@/constants/theme";

export function Sidebar({ route, setRoute }) {
  return (
    <div
      className="fixed left-0 top-0 bottom-0 flex flex-col py-5 px-3"
      style={{ width: 240, backgroundColor: C.sidebar }}
    >
      <div className="px-3 mb-8">
        <LogoMark />
      </div>
      <nav className="flex flex-col gap-0.5">
        {NAV_ITEMS.map((item) => {
          const active = route.name === item.key;
          return (
            <button
              key={item.key}
              onClick={() => setRoute({ name: item.key, id: null })}
              className="text-left px-3 py-2 rounded-md text-sm transition-all duration-200"
              style={{
                backgroundColor: active ? `${C.accent}1A` : "transparent",
                color: active ? "#fff" : "rgba(255,255,255,0.65)",
                borderLeft: active
                  ? `3px solid ${C.accent}`
                  : "3px solid transparent",
                fontWeight: active ? 500 : 400,
              }}
            >
              {item.label}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
