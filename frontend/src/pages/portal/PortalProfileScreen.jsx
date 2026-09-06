import { useState, useEffect } from "react";
import { Card } from "@/components/ui/Card";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { C } from "@/constants/theme";
import { loadPortalProfile } from "@/api/api-functions/portal";

function Field({ label, value, hint }) {
  return (
    <div>
      <div
        className="text-xs uppercase tracking-wide"
        style={{ color: C.muted }}
      >
        {label}
      </div>
      <div className="text-base" style={{ color: C.text }}>
        {value}
      </div>
      {hint && (
        <div className="text-xs mt-0.5" style={{ color: C.muted }}>
          {hint}
        </div>
      )}
    </div>
  );
}

export function PortalProfileScreen() {
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    loadPortalProfile().then(setData).catch(setLoadError);
  }, []);

  if (loadError)
    return (
      <LoadFailed error={loadError} onRetry={() => window.location.reload()} />
    );
  if (!data) return null;

  return (
    <div>
      <h1 className="text-xl font-semibold mb-1" style={{ color: C.text }}>
        Profile
      </h1>
      <p className="text-sm mb-6" style={{ color: C.muted }}>
        Your company as we have it on file.
      </p>

      <Card className="mb-6">
        <div className="grid grid-cols-2 gap-6">
          <Field label="Company" value={data.company} />
          <Field
            label="Pricing tier"
            value={data.tier}
            /* The tier decides the discount ceiling the rep is working
               against, which is what explains why a counter-offer was
               accepted or sent back for approval. */
            hint="Sets the discount your account manager can approve directly"
          />
          <Field label="Contact" value={data.contact_name} />
          <Field label="Sign-in email" value={data.contact_email} />
        </div>
      </Card>

      <Card>
        <div className="text-base font-semibold mb-4" style={{ color: C.text }}>
          At a glance
        </div>
        <div className="grid grid-cols-3 gap-6">
          <Field
            label="Quotations open"
            value={data.open_quotations}
            hint="Awaiting your decision or ours"
          />
          <Field label="Orders placed" value={data.orders} />
          <Field
            label="Outstanding"
            value={`$${data.outstanding.toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}`}
            hint="Across all unpaid invoices"
          />
        </div>
      </Card>
    </div>
  );
}
