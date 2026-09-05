import { useState } from "react";
import { PortalDevSwitch } from "@/components/layout/PortalDevSwitch";
import { PortalNav } from "@/components/layout/PortalNav";
import { Sidebar } from "@/components/layout/Sidebar";
import { C } from "@/constants/theme";
import { DashboardScreen } from "@/pages/DashboardScreen";
import { DealHealthScreen } from "@/pages/DealHealthScreen";
import { LoginScreen } from "@/pages/LoginScreen";
import { ReportsScreen } from "@/pages/ReportsScreen";
import { DiscountConfigScreen } from "@/pages/admin/DiscountConfigScreen";
import { ApprovalDetailScreen } from "@/pages/approvals/ApprovalDetailScreen";
import { ApprovalsScreen } from "@/pages/approvals/ApprovalsScreen";
import { FulfillmentDetailScreen } from "@/pages/fulfillment/FulfillmentDetailScreen";
import { FulfillmentScreen } from "@/pages/fulfillment/FulfillmentScreen";
import { InvoiceDetailScreen } from "@/pages/invoices/InvoiceDetailScreen";
import { InvoicesScreen } from "@/pages/invoices/InvoicesScreen";
import { PortalNegotiationScreen } from "@/pages/portal/PortalNegotiationScreen";
import { ProductDetailScreen } from "@/pages/products/ProductDetailScreen";
import { ProductsScreen } from "@/pages/products/ProductsScreen";
import { QuotationDetailScreen } from "@/pages/quotations/QuotationDetailScreen";
import { QuotationsScreen } from "@/pages/quotations/QuotationsScreen";
import { BillingDetailScreen } from "@/pages/subscriptions/BillingDetailScreen";
import { SubscriptionsScreen } from "@/pages/subscriptions/SubscriptionsScreen";

export default function App() {
  const [route, setRoute] = useState({ name: "login", id: null });
  const [portalTab, setPortalTab] = useState("My Quotation");

  const renderScreen = () => {
    switch (route.name) {
      case "dashboard":
        return <DashboardScreen setRoute={setRoute} />;
      case "quotations":
        return <QuotationsScreen setRoute={setRoute} />;
      case "quotation-detail":
        return (
          <QuotationDetailScreen id={route.id || "q1"} setRoute={setRoute} />
        );
      case "approvals":
        return <ApprovalsScreen setRoute={setRoute} />;
      case "approval-detail":
        return (
          <ApprovalDetailScreen id={route.id || "q1"} setRoute={setRoute} />
        );
      case "fulfillment":
        return <FulfillmentScreen setRoute={setRoute} />;
      case "fulfillment-detail":
        return (
          <FulfillmentDetailScreen id={route.id || "q5"} setRoute={setRoute} />
        );
      case "subscriptions":
        return <SubscriptionsScreen setRoute={setRoute} />;
      case "subscription-detail":
        return (
          <BillingDetailScreen id={route.id || "s1"} setRoute={setRoute} />
        );
      case "portal-negotiation":
        return <PortalNegotiationScreen />;
      case "invoices":
        return <InvoicesScreen setRoute={setRoute} />;
      case "invoice-detail":
        return (
          <InvoiceDetailScreen id={route.id || "i2"} setRoute={setRoute} />
        );
      case "deal-health":
        return <DealHealthScreen setRoute={setRoute} />;
      case "reports":
        return <ReportsScreen setRoute={setRoute} />;
      case "products":
        return <ProductsScreen setRoute={setRoute} />;
      case "product-detail":
        return (
          <ProductDetailScreen id={route.id || "p1"} setRoute={setRoute} />
        );
      case "discount-config":
        return <DiscountConfigScreen setRoute={setRoute} />;
      default:
        return <DashboardScreen setRoute={setRoute} />;
    }
  };

  if (route.name === "login") {
    return <LoginScreen setRoute={setRoute} />;
  }

  if (route.name === "portal-negotiation") {
    return (
      <div className="min-h-screen" style={{ backgroundColor: C.bg }}>
        <PortalNav portalTab={portalTab} setPortalTab={setPortalTab} />
        {renderScreen()}
        <PortalDevSwitch setRoute={setRoute} />
      </div>
    );
  }

  return (
    <div style={{ backgroundColor: C.bg, minHeight: "100vh" }}>
      <Sidebar route={route} setRoute={setRoute} />
      <div
        className="min-h-screen p-8"
        style={{ marginLeft: 240, maxWidth: 1200 + 240 }}
      >
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>{renderScreen()}</div>
      </div>
      <PortalDevSwitch setRoute={setRoute} />
    </div>
  );
}

// Small fixed link so reviewers can reach the portal + login screens, which have no
// sidebar entry point per the route map (kept unobtrusive, bottom-left corner).
