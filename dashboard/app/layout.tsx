import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";
import { Sidebar } from "@/app/components/layout/Sidebar";
import { Header } from "@/app/components/layout/Header";

export const metadata: Metadata = {
  title: "API Explorer - Discover and Monitor API Endpoints",
  description: "A modern API endpoint explorer and monitoring platform. Discover, organize, and monitor APIs across the internet.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const plausibleDomain = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN;

  return (
    <html lang="en">
      {plausibleDomain && (
        <Script
          src="https://plausible.io/js/script.js"
          data-domain={plausibleDomain}
          strategy="afterInteractive"
        />
      )}
      <body className="min-h-screen bg-bg-primary text-text-primary antialiased">
        <div className="flex">
          <Sidebar />
          <div className="flex-1 lg:ml-64 min-h-screen flex flex-col">
            <Header />
            <main className="flex-1 p-6">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}