import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { Td, Th, Tr } from "@/components/ui/Table";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { Transition } from "@/components/ui/Transition";
import { loadProducts } from "@/api/api-functions/products";

export function ProductsScreen() {
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [loadError, setLoadError] = useState(null);
  useEffect(() => {
    loadProducts().then(setData).catch(setLoadError);
  }, []);
  if (loadError)
    return (
      <LoadFailed error={loadError} onRetry={() => window.location.reload()} />
    );

  return (
    <Transition keyProp="products">
      <PageHeader
        title="Products"
        action={
          <Button variant="primary" onClick={() => navigate("/products/new")}>
            + New Product
          </Button>
        }
      />
      <div className="grid grid-cols-3 gap-4 mb-6">
        <StatCard label="Total Products" value={data.length} />
        {/* Counted from the catalogue. The card here used to read "Pricelists:
            3" - a constant, and one the list response cannot even support,
            since price lists are per tier and live on the product detail. */}
        <StatCard
          label="Categories"
          value={new Set(data.map((p) => p.category)).size}
        />
        <StatCard
          label="Variants"
          value={data.reduce((s, p) => s + p.variants, 0)}
        />
      </div>
      <Card>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Product</Th>
              <Th>Category</Th>
              <Th right>Variants</Th>
              <Th right>Price</Th>
              <Th>Unit</Th>
              <Th right>Tax</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {data.map((p) => (
              <Tr key={p.id} onClick={() => navigate(`/products/${p.id}`)}>
                <Td>{p.name}</Td>
                <Td>{p.category}</Td>
                <Td right>{p.variants}</Td>
                <Td right>${p.price.toLocaleString()}</Td>
                <Td>{p.unit}</Td>
                <Td right>{p.tax}</Td>
                <Td>
                  <Badge status={p.status} />
                </Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>
    </Transition>
  );
}
