import { useState, useEffect } from "react";
import { AdminTabs } from "@/components/admin/AdminTabs";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { C } from "@/constants/theme";
import { loadDiscountConfig } from "@/api/api-functions/admin";

export function DiscountConfigScreen() {
  const [config, setConfig] = useState(null);
  const [toast, setToast] = useState("");
  useEffect(() => {
    loadDiscountConfig().then(setConfig);
  }, []);
  if (!config) return null;

  const updateTier = (i, value) => {
    setConfig((c) => {
      const tier_ceilings = [...c.tier_ceilings];
      tier_ceilings[i] = {
        ...tier_ceilings[i],
        max_discount: Number(value) || 0,
      };
      return { ...c, tier_ceilings };
    });
  };
  const updateCategory = (i, value) => {
    setConfig((c) => {
      const category_ceilings = [...c.category_ceilings];
      category_ceilings[i] = {
        ...category_ceilings[i],
        max_discount: Number(value) || 0,
      };
      return { ...c, category_ceilings };
    });
  };

  return (
    <Transition keyProp="discount-config">
      <PageHeader title="Discount Configuration" />
      <Card className="mb-6">
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Tier Discount Ceilings
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Tier</Th>
              <Th right>Max Discount</Th>
            </tr>
          </thead>
          <tbody>
            {config.tier_ceilings.map((t, i) => (
              <Tr key={i}>
                <Td>{t.tier}</Td>
                <Td right>
                  <div className="flex justify-end items-center gap-1">
                    <input
                      type="number"
                      value={t.max_discount}
                      onChange={(e) => updateTier(i, e.target.value)}
                      className="rounded-md px-2 py-1 text-sm text-right tabular-nums outline-none transition-all duration-150"
                      style={{ border: `1px solid ${C.border}`, width: 60 }}
                    />
                    <AdminTabs />
                    <span className="text-sm" style={{ color: C.muted }}>
                      %
                    </span>
                  </div>
                </Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card className="mb-6">
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Category Discount Ceilings
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Category</Th>
              <Th right>Max Discount</Th>
            </tr>
          </thead>
          <tbody>
            {config.category_ceilings.map((t, i) => (
              <Tr key={i}>
                <Td>{t.category}</Td>
                <Td right>
                  <div className="flex justify-end items-center gap-1">
                    <input
                      type="number"
                      value={t.max_discount}
                      onChange={(e) => updateCategory(i, e.target.value)}
                      className="rounded-md px-2 py-1 text-sm text-right tabular-nums outline-none transition-all duration-150"
                      style={{ border: `1px solid ${C.border}`, width: 60 }}
                    />
                    <span className="text-sm" style={{ color: C.muted }}>
                      %
                    </span>
                  </div>
                </Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card className="mb-6">
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Approval Routing Rules
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Discount Range</Th>
              <Th>Approval Required</Th>
            </tr>
          </thead>
          <tbody>
            {config.routing_rules.map((r, i) => (
              <Tr key={i}>
                <Td>{r.range}</Td>
                <Td>{r.approval}</Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>

      <div className="text-sm mb-6" style={{ color: C.muted }}>
        Blended risk is calculated from the highest single-line discount overage
        weighted against the customer's tier ceiling — changes here take effect
        on the next quotation submitted.
      </div>

      <div className="flex justify-end">
        <Button
          variant="primary"
          onClick={() => setToast("Configuration saved")}
        >
          Save Configuration
        </Button>
      </div>
      <Toast message={toast} onClose={() => setToast("")} />
    </Transition>
  );
}
