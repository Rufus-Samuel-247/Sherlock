import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SHERLOCK — Fraud Detection & Ring Analysis",
  description:
    "Real-time financial fraud detection platform powered by graph neural networks, XGBoost, and SHAP-based explainability.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-[#06080f] text-slate-200 font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
