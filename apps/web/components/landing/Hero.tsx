import React from "react";

export function Hero(): React.ReactElement {
  return (
    <section style={{
      padding: "120px 2rem 80px",
      maxWidth: "1000px",
      margin: "0 auto",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      textAlign: "center"
    }}>
      <div style={{ marginBottom: "6rem" }}>
        <h1 style={{
          fontSize: "clamp(3rem, 6vw, 4.5rem)",
          fontWeight: 600,
          letterSpacing: "-0.04em",
          lineHeight: 1.1,
          marginBottom: "1.5rem",
          color: "var(--text-primary)"
        }}>
          Hiring, without<br/>
          the operational mess.
        </h1>
        <p style={{
          fontSize: "1.125rem",
          color: "var(--text-secondary)",
          maxWidth: "480px",
          margin: "0 auto",
          lineHeight: 1.6,
          fontWeight: 400
        }}>
          Hiron organizes jobs, resumes, candidate evaluation, and hiring decisions into one intelligent system.
        </p>
      </div>

      {/* Live Product Moment */}
      <div style={{
        width: "100%",
        maxWidth: "600px",
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
        padding: "2rem",
        display: "flex",
        flexDirection: "column",
        textAlign: "left"
      }}>
        <div style={{ marginBottom: "2rem", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600, marginBottom: "0.5rem" }}>JOB</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 600, color: "var(--text-primary)" }}>Senior Backend Engineer</div>
          </div>
          <div style={{ display: "inline-flex", alignItems: "center", padding: "0.1875rem 0.5rem", borderRadius: "var(--radius-sm)", fontSize: "0.75rem", fontWeight: 600, backgroundColor: "var(--bg-hover)", color: "var(--text-primary)", border: "1px solid var(--border-strong)" }}>
            Active
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {[
            { label: "Applications", count: 128 },
            { label: "Shortlisted", count: 17 },
            { label: "Screening", count: 8 },
            { label: "Interviews", count: 4 },
            { label: "Final candidates", count: 2 },
            { label: "Offer", count: 1 }
          ].map((stat, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.75rem 0", borderBottom: i === 5 ? "none" : "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "0.9375rem", color: "var(--text-secondary)", fontWeight: 500 }}>{stat.label}</div>
              <div style={{ fontSize: "1rem", color: "var(--text-primary)", fontWeight: 600 }}>{stat.count}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
