import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "AegisTrade",
  description: "Demo-first agentic trading bot dashboard"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

