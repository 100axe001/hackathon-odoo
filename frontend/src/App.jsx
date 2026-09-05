import { RouterProvider } from "react-router-dom";
import { SessionProvider } from "@/hooks/useSession";
import { router } from "@/routes";

export default function App() {
  return (
    <SessionProvider>
      <RouterProvider router={router} />
    </SessionProvider>
  );
}
