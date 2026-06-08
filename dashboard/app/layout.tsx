import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";
import { Sidebar } from "@/app/components/layout/sidebar";
import { Header } from "@/app/components/layout/header";
import { FeedbackButton } from "@/app/components/feedback/FeedbackButton";

export const metadata: Metadata = {
  title: "Opportunity Intelligence Platform",
  description: "Real-time startup intelligence — open-source alternative to Crunchbase",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const plausibleDomain = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN;

  return (
    <html lang="en" className="dark">
      {plausibleDomain && (
        <Script
          src="https://plausible.io/js/script.js"
          data-domain={plausibleDomain}
          strategy="afterInteractive"
        />
      )}
      <body className="min-h-screen bg-surface-primary text-zinc-50 flex">
        <Sidebar />
        <div className="flex-1 flex flex-col min-h-screen">
          <Header />
          <main className="flex-1 p-6 overflow-y-auto">{children}</main>
        </div>
        <FeedbackButton />
      </body>
    </html>
  );
}
