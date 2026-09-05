import { C } from "@/constants/theme";

export function PageHeader({ title, subtitle, action }) {
  return (
    <div className="flex items-start justify-between mb-4 gap-6">
      <div>
        <h1 className="text-xl font-semibold" style={{ color: C.text }}>
          {title}
        </h1>
        {subtitle && (
          <p className="text-sm mt-1" style={{ color: C.muted }}>
            {subtitle}
          </p>
        )}
      </div>
      {action}
    </div>
  );
}
