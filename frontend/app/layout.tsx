import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import TopNav from "@/components/nav/TopNav";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "EdgeOne QA Assistant",
  description: "AI-powered Q&A for EdgeOne documentation",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-enterprise-bg text-white min-h-screen`}>
        <TopNav />
        <main className="pt-14">{children}</main>
      </body>
    </html>
  );
}
