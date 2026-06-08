import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "PulseOps — AI-Powered Team Operations",
  description: "AI-native operational intelligence platform for modern teams",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full dark">
      <body className="h-full bg-[#020817] text-slate-100 antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
