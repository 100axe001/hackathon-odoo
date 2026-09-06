import { useNavigate, useParams } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { InfoBanner } from "@/components/ui/InfoBanner";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { Transition } from "@/components/ui/Transition";
import { ProductPicker } from "@/components/quotations/ProductPicker";
import { CustomerThread } from "@/components/quotations/CustomerThread";
import { DealJourney } from "@/components/quotations/DealJourney";
import { C } from "@/constants/theme";
import {
  deleteQuotation,
  loadQuotationDetail,
  loadUpsells,
  patchDiscount,
  patchLineQty,
  submitQuotation,
  addQuotationLine,
} from "@/api/api-functions/quotations";

// Catalogue ids come back as "p12"; the API takes the number.
function productIdOf(product) {
  return Number(String(product.id).replace(/^p/, ""));
}

export function QuotationDetailScreen() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [detail, setDetail] = useState(null);
  const [upsells, setUpsells] = useState([]);
  const [toast, setToast] = useState("");
  const [pickerOpen, setPickerOpen] = useState(false);
  const [orderDiscount, setOrderDiscount] = useState(0);
  const timers = useRef({});
  const orderTimer = useRef(null);
  const [outcome, setOutcome] = useState(null);
  const [loadError, setLoadError] = useState(null);
  // Two-step rather than a browser confirm(): the row and everything under it
  // goes, so the second click names what it is about to destroy.
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  useEffect(() => {
    setLoadError(null);
    // Catch both: deleting a quotation and then pressing Back asks for one that
    // is gone, and an uncaught 404 left this screen permanently blank with the
    // failure only visible in the console.
    loadQuotationDetail(id).then(setDetail).catch(setLoadError);
    loadUpsells(id)
      .then(setUpsells)
      .catch(() => setUpsells([]));
  }, [id]);

  if (loadError)
    return (
      <LoadFailed
        error={loadError}
        onRetry={
          loadError.status === 404
            ? () => navigate("/quotations")
            : () => window.location.reload()
        }
        retryLabel={
          loadError.status === 404 ? "Back to quotations" : "Try again"
        }
      />
    );
  if (!detail) return null;

  // Optimistic, then reconciled. Quantity moves the line total and the blended
  // weighting, so the server re-scores and sends back the margin it computed -
  // the screen never works it out itself.
  const updateQty = async (lineId, delta) => {
    const line = detail.lines.find((l) => l.id === lineId);
    const next = Math.max(1, line.qty + delta);
    if (next === line.qty) return;

    const previous = line.qty;
    setDetail((d) => ({
      ...d,
      lines: d.lines.map((l) => (l.id === lineId ? { ...l, qty: next } : l)),
    }));

    try {
      const res = await patchLineQty(id, lineId, next);
      setDetail((d) => ({
        ...d,
        margin: res.margin,
        margin_pct: res.margin_pct,
        lines: d.lines.map((l) =>
          l.id === lineId ? { ...l, qty: res.qty, status: res.status } : l,
        ),
      }));
    } catch (err) {
      setDetail((d) => ({
        ...d,
        lines: d.lines.map((l) =>
          l.id === lineId ? { ...l, qty: previous } : l,
        ),
      }));
      setToast(err.detail || "Could not change that quantity.");
    }
  };

  const updateDiscount = (lineId, value) => {
    const pct = Math.max(0, Number(value) || 0);
    setDetail((d) => ({
      ...d,
      lines: d.lines.map((l) =>
        l.id === lineId ? { ...l, discount_pct: pct } : l,
      ),
    }));
    clearTimeout(timers.current[lineId]);
    timers.current[lineId] = setTimeout(async () => {
      try {
        const res = await patchDiscount(id, lineId, pct);
        setDetail((d) => ({
          ...d,
          margin: res.margin,
          margin_pct: res.margin_pct,
          lines: d.lines.map((l) =>
            l.id === lineId
              ? {
                  ...l,
                  status: res.status,
                  limit_pct: res.allowed_discount_pct,
                }
              : l,
          ),
        }));
      } catch (err) {
        setToast(err.detail || "Could not save that discount.");
      }
    }, 400);
  };

  // PS section 4 B5 pairs "Add to Quote" with "Dismiss" - a rep needs to clear a
  // suggestion that is wrong for this customer without adding it.
  const dismissUpsell = (index) => {
    setUpsells((list) => list.filter((_, i) => i !== index));
  };

  // Goes through the server exactly as the upsell path does. The old version
  // invented a line id and guessed the discount ceiling from the category,
  // which meant the line never persisted and the ceiling was a frontend rule.
  const addCatalogueLine = async (product) => {
    try {
      const updated = await addQuotationLine(id, productIdOf(product), 1);
      setDetail(updated);
      setToast(`${product.name} added`);
      loadUpsells(id)
        .then(setUpsells)
        .catch(() => {});
    } catch (err) {
      setToast(err.detail || "Could not add that product.");
    }
  };

  // PS section 4 B3 allows an order-level discount. It is pushed down onto every
  // line rather than held separately, so each line is still checked against its
  // own ceiling - otherwise an order-level figure would bypass governance.
  const applyOrderDiscount = (value) => {
    const pct = Math.max(0, Number(value) || 0);
    setOrderDiscount(pct);
    setDetail((d) => ({
      ...d,
      lines: d.lines.map((l) => ({ ...l, discount_pct: pct })),
    }));

    // Debounced, because this is an onChange: writing every line on every
    // keystroke would be one request per line per character. Each line is still
    // patched individually, so each is checked against its own ceiling.
    clearTimeout(orderTimer.current);
    orderTimer.current = setTimeout(async () => {
      try {
        for (const line of detail.lines) {
          await patchDiscount(id, line.id, pct);
        }
        setDetail(await loadQuotationDetail(id));
      } catch (err) {
        setToast(err.detail || "Could not apply that discount.");
      }
    }, 500);
  };

  // The server adds the line, re-scores, and returns the whole detail with the
  // updated margin. The old version invented a line client-side and guessed its
  // price from the margin delta, so the totals were fiction.
  const addUpsellLine = async (product) => {
    try {
      const updated = await addQuotationLine(id, product.product_id, 1);
      setDetail(updated);
      setToast(`${product.product} added`);
      loadUpsells(id).then(setUpsells);
    } catch {
      setToast("Could not add that product.");
    }
  };

  // Margin comes from the server, computed against each line's real cost_price.
  // The client used to assume a flat 22% on every product, which meant the
  // number moved plausibly but was never right.
  // Editing after submission would let a rep change the terms a reviewer is
  // looking at, so the builder locks itself outside Draft.
  const editable = detail.status === "Draft";

  const margin = detail.margin ?? 0;
  const marginPct = detail.margin_pct ?? 0;

  // The backend decides. The client no longer guesses from the line badges -
  // a quote can be routed for approval by the blended path even when no single
  // line looks bad, which the old check could never have caught.
  // Whether this is deletable is the server's call - it owns the ownership and
  // billing rules - so the screen only renders what came back on the payload.
  const remove = async () => {
    try {
      await deleteQuotation(id);
      navigate("/quotations");
    } catch (err) {
      setConfirmingDelete(false);
      setToast(err.detail || "Could not delete this quotation.");
    }
  };

  const submit = async () => {
    try {
      const result = await submitQuotation(id);

      // Re-read before anything else: the badge in the header and the action
      // bar both key off status, and leaving them stale is what made the screen
      // look like nothing had happened.
      setDetail(await loadQuotationDetail(id));

      // Shown in place rather than as a toast. This is the most important
      // sentence the app produces, and the old version flashed it for two
      // seconds and then navigated away from it.
      setOutcome(result);
    } catch (err) {
      setToast(err.detail || "Could not submit this quotation.");
    }
  };

  return (
    <Transition keyProp={`qd-${id}`}>
      <DealJourney quotationId={id} />
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold" style={{ color: C.text }}>
            {detail.number} — {detail.customer_name}
          </h1>
          {/* The price list follows the customer's tier, so it is shown rather
              than chosen. The old dropdown offered options it could not apply. */}
          <div className="text-sm mt-1" style={{ color: C.muted }}>
            {detail.price_list} pricing
          </div>
        </div>
        <div className="flex items-center gap-2">
          {detail.risk_level && (
            <Badge
              status={detail.risk_level}
              label={`Risk: ${detail.risk_level}`}
            />
          )}
          <Badge status={detail.status} />
          {detail.can_delete &&
            (confirmingDelete ? (
              <>
                <span className="text-sm" style={{ color: C.dangerText }}>
                  Delete {detail.number} and everything on it?
                </span>
                <Button
                  variant="secondary"
                  onClick={() => setConfirmingDelete(false)}
                >
                  Keep
                </Button>
                <Button variant="destructive" onClick={remove}>
                  Delete
                </Button>
              </>
            ) : (
              <Button
                variant="destructive"
                onClick={() => setConfirmingDelete(true)}
              >
                Delete
              </Button>
            ))}
        </div>
      </div>

      {/* A returned quotation used to arrive as an ordinary Draft. The rep had
          no way to tell it apart from one never submitted, and the reviewer's
          reason sat in an audit trail this screen does not show. */}
      {!outcome && detail.returned_by && (
        <div className="mb-6">
          <InfoBanner tone="warn">
            Sent back by {detail.returned_by} for revision
            {detail.returned_note ? `: "${detail.returned_note}"` : "."} Adjust
            the lines below and submit again — it is re-scored from scratch, so
            a smaller discount may need fewer reviewers.
          </InfoBanner>
        </div>
      )}

      {outcome && (
        <div className="mb-6">
          <InfoBanner
            tone={outcome.required_approval.length ? "warn" : "success"}
            action={
              outcome.required_approval.length ? (
                <Button
                  variant="secondary"
                  onClick={() => navigate(`/approvals/${id}`)}
                >
                  Open approval
                </Button>
              ) : null
            }
          >
            {outcome.required_approval.length
              ? `${outcome.risk_level} risk — routed to ${outcome.required_approval.join(" then ")}. ${outcome.explanation}`
              : `Within every ceiling, so no review was needed. ${outcome.explanation}`}
          </InfoBanner>
        </div>
      )}

      <div className="flex items-center justify-between mb-3">
        <div className="text-base font-semibold" style={{ color: C.text }}>
          Order Lines
        </div>
        {editable ? (
          <Button variant="secondary" onClick={() => setPickerOpen(true)}>
            + Add Product
          </Button>
        ) : (
          <span className="text-sm" style={{ color: C.muted }}>
            Locked while this quotation is {detail.status.toLowerCase()}
          </span>
        )}
      </div>

      <Card className="mb-6">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Product</Th>
              <Th right>Qty</Th>
              <Th right>Price</Th>
              <Th right>Discount</Th>
              <Th right>Limit</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {detail.lines.map((line) => (
              <Tr key={line.id}>
                <Td>{line.product}</Td>
                <Td right>
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => updateQty(line.id, -1)}
                      className="rounded-md w-6 h-6 text-sm transition-colors duration-150"
                      style={{ border: `1px solid ${C.border}`, color: C.text }}
                    >
                      −
                    </button>
                    <span
                      className="tabular-nums"
                      style={{ minWidth: 24, textAlign: "center" }}
                    >
                      {line.qty}
                    </span>
                    <button
                      onClick={() => updateQty(line.id, 1)}
                      className="rounded-md w-6 h-6 text-sm transition-colors duration-150"
                      style={{ border: `1px solid ${C.border}`, color: C.text }}
                    >
                      +
                    </button>
                  </div>
                </Td>
                <Td right>${line.price.toLocaleString()}</Td>
                <Td right>
                  <div className="flex items-center justify-end gap-1">
                    <input
                      type="number"
                      value={line.discount_pct}
                      onChange={(e) => updateDiscount(line.id, e.target.value)}
                      className="rounded-md px-2 py-1 text-sm text-right tabular-nums outline-none transition-all duration-150"
                      style={{ border: `1px solid ${C.border}`, width: 56 }}
                    />
                    <span className="text-sm" style={{ color: C.muted }}>
                      %
                    </span>
                  </div>
                </Td>
                <Td right className="text-xs" style={{ color: C.muted }}>
                  {line.limit_pct}%
                </Td>
                <Td>
                  <Badge
                    status={line.status}
                    label={
                      line.status === "OVER"
                        ? `OVER (+${(line.discount_pct - line.limit_pct).toFixed(0)}pt)`
                        : "OK"
                    }
                  />
                </Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>

      <CustomerThread quotationId={id} />

      <div className="mb-3 text-base font-semibold" style={{ color: C.text }}>
        Suggested Upsells
      </div>
      {/* An empty grid under a heading reads as a broken panel. Say why there
          is nothing: suggestions come from what is already on the quote, so a
          quotation with no lines has nothing to pair against. */}
      {upsells.length === 0 && (
        <div
          className="rounded-lg px-4 py-6 mb-6 text-sm text-center"
          style={{ backgroundColor: C.neutralBg, color: C.muted }}
        >
          {detail.lines.length === 0
            ? "Add a product first — suggestions are based on what is already on the quotation."
            : "Nothing to suggest for these products yet. Pairings and the minimum margin are set in Back-end → Discount Tiers."}
        </div>
      )}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {upsells.map((u, i) => (
          <div
            key={i}
            className="rounded-lg p-4 bg-white flex flex-col gap-2"
            style={{ border: `1px dashed ${C.border}` }}
          >
            <div className="text-sm font-medium" style={{ color: C.text }}>
              {u.product}
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <Badge
                status="OK"
                label={`Margin +$${u.margin_delta.toLocaleString()}`}
              />
              {u.promo_tag && <Badge status="Pending" label={u.promo_tag} />}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <Button
                variant="secondary"
                disabled={!editable}
                onClick={() => addUpsellLine(u)}
              >
                Add to Quote
              </Button>
              <button
                onClick={() => dismissUpsell(i)}
                className="text-xs px-2 py-1 transition-colors duration-150"
                style={{ color: C.muted }}
              >
                Dismiss
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="text-sm" style={{ color: C.muted }}>
              Order discount
            </span>
            <input
              type="number"
              value={orderDiscount}
              onChange={(e) => applyOrderDiscount(e.target.value)}
              className="rounded-md px-2 py-1 text-sm text-right tabular-nums outline-none transition-all duration-150"
              style={{ border: `1px solid ${C.border}`, width: 60 }}
            />
            <span className="text-sm" style={{ color: C.muted }}>
              %
            </span>
          </div>
          <div className="text-sm" style={{ color: C.muted }}>
            Estimated margin:{" "}
            <span
              className="font-semibold tabular-nums"
              style={{ color: C.text }}
            >
              ${margin.toLocaleString()}
              <span className="font-normal ml-1" style={{ color: C.muted }}>
                ({marginPct}%)
              </span>
            </span>
          </div>
        </div>
        <div className="flex gap-3">
          {editable ? (
            <Button variant="primary" onClick={submit}>
              Submit for Approval
            </Button>
          ) : (
            <Button variant="secondary" onClick={() => navigate("/approvals")}>
              View in Approvals
            </Button>
          )}
        </div>
      </div>
      <ProductPicker
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onAdd={addCatalogueLine}
      />
      <Toast message={toast} onClose={() => setToast("")} />
    </Transition>
  );
}
