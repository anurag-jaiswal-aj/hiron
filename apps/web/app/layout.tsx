import "./globals.css";
import { AuthProvider } from "../context/AuthContext";
import BackgroundGrid from "../components/ui/BackgroundGrid";

export const dynamic = 'force-dynamic';

export const metadata = {
  title: "Hiron — AI-Powered Hiring Intelligence Platform",
  description: "Multi-tenant AI recruitment platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  return (
    <html lang="en">
      <body>
        <BackgroundGrid />
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
