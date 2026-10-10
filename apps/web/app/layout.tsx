import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ARG | Runtime Governance Console",
  description: "Review and govern AI agent actions before execution.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
