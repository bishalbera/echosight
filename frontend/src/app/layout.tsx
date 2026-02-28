import type { Metadata } from "next";
import "./globals.css";
// Stream Video SDK styles — imported here so they apply globally
// and avoid Next.js App Router restrictions on CSS in client components
import "@stream-io/video-react-sdk/dist/css/styles.css";

export const metadata: Metadata = {
  title: "EchoSight",
  description: "Real-time social intelligence for the visually impaired",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
