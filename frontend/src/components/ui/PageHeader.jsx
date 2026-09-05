import { C } from "@/constants/theme";

export function PageHeader({ title, action }) {
  return (
    <div className="flex items-center justify-between mb-6">
      <h1 className="text-xl font-semibold" style={{ color: C.text }}>
        {title}
      </h1>
      {action}
    </div>
  );
}
