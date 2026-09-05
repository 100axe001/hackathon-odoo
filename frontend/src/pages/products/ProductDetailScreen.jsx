import { useParams } from "react-router-dom";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FilterPill } from "@/components/ui/FilterPill";
import { Input } from "@/components/ui/Input";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { C } from "@/constants/theme";
import { loadProductDetail } from "@/api/api-functions/products";

export function ProductDetailScreen() {
  const { id } = useParams();
  const [detail, setDetail] = useState(null);
  const [toast, setToast] = useState("");
  useEffect(() => {
    loadProductDetail(id).then(setDetail);
  }, [id]);
  if (!detail) return null;
  return (
    <Transition keyProp={`pd-${id}`}>
      <PageHeader title={detail.name} />
      <Card className="mb-6">
        <div className="text-base font-semibold mb-4" style={{ color: C.text }}>
          General Info
        </div>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-sm mb-1 block" style={{ color: C.text }}>
              Product Name
            </label>
            <Input value={detail.name} onChange={() => {}} />
          </div>
          <div>
            <label className="text-sm mb-1 block" style={{ color: C.text }}>
              Category
            </label>
            <Input value={detail.category} onChange={() => {}} />
          </div>
          <div>
            <label className="text-sm mb-1 block" style={{ color: C.text }}>
              Price
            </label>
            <Input type="number" value={detail.price} onChange={() => {}} />
          </div>
          <div>
            <label className="text-sm mb-1 block" style={{ color: C.text }}>
              Unit
            </label>
            <Input value={detail.unit} onChange={() => {}} />
          </div>
          <div>
            <label className="text-sm mb-1 block" style={{ color: C.text }}>
              Tax %
            </label>
            <Input type="number" value={detail.tax} onChange={() => {}} />
          </div>
          <div>
            <label className="text-sm mb-1 block" style={{ color: C.text }}>
              Quantity on Hand
            </label>
            <Input
              type="number"
              value={detail.qty_on_hand}
              onChange={() => {}}
            />
          </div>
        </div>
        <div className="mb-4">
          <label className="text-sm mb-1 block" style={{ color: C.text }}>
            Description
          </label>
          <textarea
            defaultValue={detail.description}
            rows={3}
            className="w-full rounded-md px-3 py-2 text-sm outline-none transition-all duration-150"
            style={{ border: `1px solid ${C.border}` }}
          />
        </div>
        <SubscriptionToggle detail={detail} />
      </Card>

      <Card className="mb-6">
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Product Variants
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Attribute</Th>
              <Th>Values</Th>
              <Th right>Extra Price</Th>
            </tr>
          </thead>
          <tbody>
            {detail.variants.map((v, i) => (
              <Tr key={i}>
                <Td>{v.attribute}</Td>
                <Td className="text-xs" style={{ color: C.muted }}>
                  {v.values}
                </Td>
                <Td right>{v.extra_price ? `+$${v.extra_price}` : "—"}</Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card className="mb-6">
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Pricelists
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Tier</Th>
              <Th>Currency</Th>
              <Th>Price Rule</Th>
            </tr>
          </thead>
          <tbody>
            {detail.pricelists.map((p, i) => (
              <Tr key={i}>
                <Td>{p.tier}</Td>
                <Td>{p.currency}</Td>
                <Td>{p.price_rule}</Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>
      <div className="flex justify-end">
        <Button variant="primary" onClick={() => setToast("Product saved")}>
          Save Changes
        </Button>
      </div>
      <Toast message={toast} onClose={() => setToast("")} />
    </Transition>
  );
}

export function SubscriptionToggle({ detail }) {
  const [isSub, setIsSub] = useState(detail.subscription);
  const [cadence, setCadence] = useState(detail.cadence);
  return (
    <div>
      <label className="text-sm mb-1 block" style={{ color: C.text }}>
        Subscription Product
      </label>
      <div className="flex gap-2 mb-2">
        <FilterPill active={isSub} onClick={() => setIsSub(true)}>
          Yes
        </FilterPill>
        <FilterPill active={!isSub} onClick={() => setIsSub(false)}>
          No
        </FilterPill>
      </div>
      <div
        className="overflow-hidden transition-all duration-200"
        style={{ maxHeight: isSub ? 80 : 0, opacity: isSub ? 1 : 0 }}
      >
        <label className="text-sm mb-1 block" style={{ color: C.text }}>
          Billing Cadence
        </label>
        <div style={{ width: 200 }}>
          <Select
            value={cadence}
            onChange={(e) => setCadence(e.target.value)}
            options={["Monthly", "Quarterly", "Yearly"]}
          />
        </div>
      </div>
    </div>
  );
}
