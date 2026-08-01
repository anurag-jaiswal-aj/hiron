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
      <body>{children}</body>
    </html>
  );
}
