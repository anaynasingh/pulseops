import { redirect } from "next/navigation";

/**
 * Root route → redirect to /dashboard
 * Auth check is handled by (dashboard)/layout.tsx
 */
export default function RootPage() {
  redirect("/dashboard");
}
