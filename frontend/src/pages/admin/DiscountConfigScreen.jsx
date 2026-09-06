import { useState, useEffect } from "react";
import { AdminTabs } from "@/components/admin/AdminTabs";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { C } from "@/constants/theme";
import {
  deleteCategoryCeiling,
  deleteDiscountTier,
  loadDiscountConfig,
  loadUpsellRule,
  saveApprovalRules,
  saveDiscountConfig,
  saveUpsellRule,
} from "@/api/api-functions/admin";
import { Select } from "@/components/ui/Select";

export function DiscountConfigScreen() {
  const [config, setConfig] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [upsell, setUpsell] = useState(null);
  const [toast, setToast] = useState("");
  useEffect(() => {
    loadDiscountConfig().then(setConfig).catch(setLoadError);
    loadUpsellRule().then(setUpsell);
  }, []);
  if (loadError)
    return (
      <LoadFailed error={loadError} onRetry={() => window.location.reload()} />
    );
  if (!config) return null;

  // The chains an admin would realistically pick, phrased the way PS 4-A3
  // phrases them. Order matters: it is who acts first, then second.
  const CHAINS = {
    "Sales Manager only": ["SALES_MANAGER"],
    "Sales Manager, then Finance": ["SALES_MANAGER", "FINANCE"],
    "Finance only": ["FINANCE"],
    "No approval needed": [],
  };

  const chainLabel = (roles) =>
    Object.keys(CHAINS).find(
      (k) => CHAINS[k].join(",") === (roles ?? []).join(","),
    ) ?? "Sales Manager only";

  const setChain = (level, label) =>
    setConfig((c) => ({
      ...c,
      chain: c.chain.map((row) =>
        row.level === level ? { ...row, roles: CHAINS[label] } : row,
      ),
    }));

  const addTier = () =>
    setConfig((c) => ({
      ...c,
      tier_ceilings: [
        ...c.tier_ceilings,
        { tier: "", max_discount: 5, isNew: true },
      ],
    }));

  const addCategory = () =>
    setConfig((c) => ({
      ...c,
      category_ceilings: [
        ...c.category_ceilings,
        { category: "", max_discount: 10, isNew: true },
      ],
    }));

  // A tier customers are on cannot go, and the server says so rather than
  // leaving those customers without a discount ceiling.
  const removeTier = async (tier, index) => {
    if (config.tier_ceilings[index]?.isNew) {
      setConfig((c) => ({
        ...c,
        tier_ceilings: c.tier_ceilings.filter((_, i) => i !== index),
      }));
      return;
    }
    try {
      setConfig(await deleteDiscountTier(tier));
      setToast(`${tier} removed`);
    } catch (err) {
      setToast(err.detail || "Could not remove that tier.");
    }
  };

  const removeCategory = async (category, index) => {
    if (config.category_ceilings[index]?.isNew) {
      setConfig((c) => ({
        ...c,
        category_ceilings: c.category_ceilings.filter((_, i) => i !== index),
      }));
      return;
    }
    try {
      setConfig(await deleteCategoryCeiling(category));
      setToast(
        `${category} ceiling removed - those lines now fall back to the customer's tier limit`,
      );
    } catch (err) {
      setToast(err.detail || "Could not remove that ceiling.");
    }
  };

  const renameTier = (i, value) =>
    setConfig((c) => {
      const tier_ceilings = [...c.tier_ceilings];
      tier_ceilings[i] = { ...tier_ceilings[i], tier: value };
      return { ...c, tier_ceilings };
    });

  const renameCategory = (i, value) =>
    setConfig((c) => {
      const category_ceilings = [...c.category_ceilings];
      category_ceilings[i] = { ...category_ceilings[i], category: value };
      return { ...c, category_ceilings };
    });

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

  // The ceilings feed the engine directly, so a saved change reroutes the next
  // submit. Echo the server's version back rather than trusting local state.
  const save = async () => {
    try {
      const tiers = config.tier_ceilings.filter((t) => t.tier.trim());
      const categories = config.category_ceilings.filter((c) =>
        c.category.trim(),
      );
      if (
        tiers.length !== config.tier_ceilings.length ||
        categories.length !== config.category_ceilings.length
      ) {
        setToast("Give every new row a name before saving");
        return;
      }
      await saveDiscountConfig(tiers, categories);

      // The chain is sent whole, and sent second: the ceilings decide a
      // quotation's risk level and these rules decide who then signs it off,
      // so saving them in this order never leaves a level without reviewers.
      const rules = (config.chain ?? []).flatMap((row) =>
        row.roles.map((role, i) => ({
          level: row.level,
          step_order: i + 1,
          role,
        })),
      );
      const saved = rules.length
        ? await saveApprovalRules(rules)
        : await loadDiscountConfig();

      if (upsell) {
        await saveUpsellRule(upsell.min_margin_pct, upsell.max_suggestions);
      }

      setConfig(saved);
      setToast(
        "Configuration saved - it applies to the next quotation submitted",
      );
    } catch (err) {
      setToast(err.detail || "Only an admin may change this configuration.");
    }
  };

  return (
    <Transition keyProp="discount-config">
      <PageHeader title="Discount Configuration" />
      <AdminTabs />
      <Card className="mb-6">
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Tier Discount Ceilings
        </div>
        <div className="mb-3">
          <Button variant="secondary" onClick={addTier}>
            + Add Tier
          </Button>
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Tier</Th>
              <Th right>Max Discount</Th>
              <Th right>Remove</Th>
            </tr>
          </thead>
          <tbody>
            {config.tier_ceilings.map((t, i) => (
              <Tr key={i}>
                <Td>
                  {t.isNew ? (
                    <input
                      value={t.tier}
                      autoFocus
                      placeholder="Tier name"
                      onChange={(e) => renameTier(i, e.target.value)}
                      className="rounded-md px-2 py-1 text-sm outline-none transition-all duration-150"
                      style={{ border: `1px solid ${C.border}`, width: 170 }}
                    />
                  ) : (
                    t.tier
                  )}
                </Td>
                <Td right>
                  <div className="flex justify-end items-center gap-1">
                    <input
                      type="number"
                      value={t.max_discount}
                      onChange={(e) => updateTier(i, e.target.value)}
                      className="rounded-md px-2 py-1 text-sm text-right tabular-nums outline-none transition-all duration-150"
                      style={{ border: `1px solid ${C.border}`, width: 60 }}
                    />
                    <span className="text-sm" style={{ color: C.muted }}>
                      %
                    </span>
                  </div>
                </Td>
                <Td right>
                  <button
                    onClick={() => removeTier(t.tier, i)}
                    className="text-xs rounded-md px-2 py-1 transition-colors duration-150"
                    style={{
                      color: C.dangerText,
                      border: `1px solid ${C.border}`,
                    }}
                  >
                    Remove
                  </button>
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
        <div className="mb-3">
          <Button variant="secondary" onClick={addCategory}>
            + Add Category
          </Button>
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Category</Th>
              <Th right>Max Discount</Th>
              <Th right>Remove</Th>
            </tr>
          </thead>
          <tbody>
            {config.category_ceilings.map((t, i) => (
              <Tr key={i}>
                <Td>
                  {t.isNew ? (
                    <input
                      value={t.category}
                      autoFocus
                      placeholder="Category name"
                      onChange={(e) => renameCategory(i, e.target.value)}
                      className="rounded-md px-2 py-1 text-sm outline-none transition-all duration-150"
                      style={{ border: `1px solid ${C.border}`, width: 170 }}
                    />
                  ) : (
                    t.category
                  )}
                </Td>
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
                <Td right>
                  <button
                    onClick={() => removeCategory(t.category, i)}
                    className="text-xs rounded-md px-2 py-1 transition-colors duration-150"
                    style={{
                      color: C.dangerText,
                      border: `1px solid ${C.border}`,
                    }}
                  >
                    Remove
                  </button>
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

        {/* The prose above is generated from these rules, so changing a chain
            here rewrites the sentence a rep reads. PS 4-A3. */}
        <div
          className="mt-5 pt-4"
          style={{ borderTop: `1px solid ${C.border}` }}
        >
          <div className="text-sm font-medium mb-3" style={{ color: C.text }}>
            Who reviews each risk level
          </div>
          <div className="flex flex-col gap-3">
            {(config.chain ?? []).map((row) => (
              <div key={row.level} className="flex items-center gap-4">
                <Badge status={row.level} label={row.level} />
                <Select
                  value={chainLabel(row.roles)}
                  onChange={(e) => setChain(row.level, e.target.value)}
                  options={Object.keys(CHAINS)}
                />
              </div>
            ))}
          </div>
        </div>
      </Card>

      {upsell && (
        <Card className="mb-6">
          <div
            className="text-base font-semibold mb-1"
            style={{ color: C.text }}
          >
            Upsell Suggestion Rule
          </div>
          <p className="text-sm mb-4" style={{ color: C.muted }}>
            Only products clearing this margin are suggested to a rep. Raising
            the floor removes thin-margin items from the panel entirely.
          </p>
          <div className="flex items-end gap-6 flex-wrap">
            <div>
              <label className="block text-xs mb-1" style={{ color: C.muted }}>
                Minimum margin %
              </label>
              <input
                type="number"
                min="0"
                max="100"
                value={upsell.min_margin_pct}
                onChange={(e) =>
                  setUpsell((u) => ({
                    ...u,
                    min_margin_pct: Math.max(0, Number(e.target.value) || 0),
                  }))
                }
                className="rounded-md px-2 py-1.5 text-sm text-right tabular-nums outline-none"
                style={{ border: `1px solid ${C.border}`, width: 80 }}
              />
            </div>
            <div>
              <label className="block text-xs mb-1" style={{ color: C.muted }}>
                Max suggestions
              </label>
              <input
                type="number"
                min="1"
                max="20"
                value={upsell.max_suggestions}
                onChange={(e) =>
                  setUpsell((u) => ({
                    ...u,
                    max_suggestions: Math.max(1, Number(e.target.value) || 1),
                  }))
                }
                className="rounded-md px-2 py-1.5 text-sm text-right tabular-nums outline-none"
                style={{ border: `1px solid ${C.border}`, width: 80 }}
              />
            </div>
          </div>
        </Card>
      )}

      <div className="text-sm mb-6" style={{ color: C.muted }}>
        Blended risk is calculated from the highest single-line discount overage
        weighted against the customer's tier ceiling — changes here take effect
        on the next quotation submitted.
      </div>

      <div className="flex justify-end">
        <Button variant="primary" onClick={save}>
          Save Configuration
        </Button>
      </div>
      <Toast message={toast} onClose={() => setToast("")} />
    </Transition>
  );
}
