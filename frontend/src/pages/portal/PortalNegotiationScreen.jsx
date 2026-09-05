import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { InfoBanner } from "@/components/ui/InfoBanner";
import { Input } from "@/components/ui/Input";
import { Transition } from "@/components/ui/Transition";
import { C } from "@/constants/theme";
import { MOCK_PORTAL_QUOTATION } from "@/api/mocks";

export function PortalNegotiationScreen() {
  const [detail] = useState(MOCK_PORTAL_QUOTATION);
  const [status, setStatus] = useState(detail.status);
  const [counterDiscount, setCounterDiscount] = useState("");
  const [deliveryDate, setDeliveryDate] = useState("");
  const [showBanner, setShowBanner] = useState(false);

  const confirm = () => {
    const pct = Number(counterDiscount) || 0;
    if (pct > 15) {
      setStatus("Pending Approval");
      setShowBanner(true);
    } else {
      setStatus("Confirmed");
    }
  };

  return (
    <div className="max-w-[760px] mx-auto py-10 px-6">
      <div className="mb-6">
        <Badge
          status={status === "Confirmed" ? "Confirmed" : "Pending Approval"}
          label={status}
        />
      </div>

      {showBanner && (
        <Transition keyProp="banner">
          <div className="mb-6">
            <InfoBanner tone="warn">
              Status changed to Pending Approval — terms exceeded threshold
            </InfoBanner>
          </div>
        </Transition>
      )}

      <Card className="mb-6">
        <div className="text-base font-semibold mb-4" style={{ color: C.text }}>
          Line Comments
        </div>
        <div className="flex flex-col gap-4">
          {detail.lines.map((l, i) => (
            <div key={i}>
              <div
                className="text-sm font-medium mb-1.5"
                style={{ color: C.text }}
              >
                {l.product}
              </div>
              <div
                className="rounded-lg px-4 py-3 text-sm"
                style={{
                  backgroundColor: C.bg,
                  color: C.text,
                  borderRadius: "12px 12px 12px 2px",
                }}
              >
                {l.comment}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="mb-6">
        <div className="flex gap-4 mb-4">
          <div className="flex-1">
            <label className="text-sm mb-1 block" style={{ color: C.text }}>
              Counter Discount %
            </label>
            <Input
              type="number"
              value={counterDiscount}
              onChange={(e) => setCounterDiscount(e.target.value)}
              placeholder="e.g. 12"
            />
          </div>
          <div className="flex-1">
            <label className="text-sm mb-1 block" style={{ color: C.text }}>
              Requested Delivery Date
            </label>
            <Input
              type="date"
              value={deliveryDate}
              onChange={(e) => setDeliveryDate(e.target.value)}
            />
          </div>
        </div>
        <div className="text-sm mb-4" style={{ color: C.muted }}>
          If final terms exceed approval thresholds, the quote automatically
          re-enters approval.
        </div>
        <div className="flex gap-3">
          <Button variant="secondary">Submit Request</Button>
          <Button variant="primary" onClick={confirm}>
            Confirm Quotation
          </Button>
        </div>
      </Card>
    </div>
  );
}
