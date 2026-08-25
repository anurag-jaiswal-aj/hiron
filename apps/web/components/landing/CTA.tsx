import React from "react";
import Link from "next/link";

export function CTA(): React.ReactElement {
  return (
    <section style={{ padding: "8rem 2rem", backgroundColor: "var(--bg-app)", borderTop: "1px solid var(--border-subtle)" }}>
      <div style={{ maxWidth: "1200px", margin: "0 auto", display: "flex", flexDirection: "column" }}>
        <h2 style={{ fontSize: "clamp(2rem, 4vw, 3rem)", fontWeight: 600, color: "var(--text-primary)", marginBottom: "1rem", letterSpacing: "-0.04em" }}>
          Ready to build your team?
        </h2>
        <p style={{ fontSize: "1.125rem", color: "var(--text-secondary)", marginBottom: "3rem" }}>
          Join the teams using Hiron to organize their hiring.
        </p>
        <div>
          <Link href="/login" style={{
            padding: "0.75rem 1.5rem",
            backgroundColor: "var(--text-primary)",
            color: "var(--bg-app)",
            fontWeight: 600,
            borderRadius: "2px",
            fontSize: "0.875rem"
          }}>
            Get started
          </Link>
        </div>
      </div>
    </section>
  );
}
