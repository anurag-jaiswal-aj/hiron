import React from "react";
import Link from "next/link";
import Image from "next/image";

export function Footer(): React.ReactElement {
  return (
    <footer style={{ padding: "4rem 2rem", backgroundColor: "var(--bg-app)", borderTop: "1px solid var(--border-subtle)" }}>
      <div style={{ maxWidth: "1200px", margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center" }} className="responsive-footer">
        <Image src="/hiron-logo-white.png" alt="Hiron Logo" width={24} height={24} style={{ height: "24px", width: "auto", opacity: 0.8 }} />

        <div style={{ display: "flex", gap: "2rem" }}>
          <Link href="/login" style={{ fontSize: "0.875rem", color: "var(--text-secondary)", fontWeight: 500 }}>Log in</Link>
          <Link href="#" style={{ fontSize: "0.875rem", color: "var(--text-secondary)", fontWeight: 500 }}>Privacy</Link>
          <Link href="#" style={{ fontSize: "0.875rem", color: "var(--text-secondary)", fontWeight: 500 }}>Terms</Link>
        </div>
      </div>
      <style dangerouslySetInnerHTML={{__html: `
        @media (max-width: 768px) {
          .responsive-footer { flex-direction: column !important; align-items: flex-start !important; gap: 2rem !important; }
        }
      `}} />
    </footer>
  );
}
