import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Transition } from "@/components/ui/Transition";
import { loadProducts } from "@/api/api-functions/products";

export function ProductsScreen() {
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  useEffect(() => {
    loadProducts().then(setData);
  }, []);
  return (
    <Transition keyProp="products">
      <PageHeader
        title="Products"
        action={<Button variant="primary">+ New Product</Button>}
      />
      <div className="grid grid-cols-3 gap-4 mb-6">
        <StatCard label="Total Products" value={data.length} />
        <StatCard label="Pricelists" value="3" />
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
