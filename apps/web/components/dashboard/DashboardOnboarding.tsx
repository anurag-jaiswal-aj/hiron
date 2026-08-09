import React from "react";
import Link from "next/link";
import { Button } from "../ui/Button";

export function DashboardOnboarding(): React.ReactElement {
  return (
    <div style={{ 
      padding: "3rem", 
      textAlign: "center", 
      backgroundColor: "var(--bg-surface)",
      border: "1px solid var(--border-subtle)",
      borderRadius: "var(--radius-lg)",
      maxWidth: "600px",
      margin: "4rem auto",
      boxShadow: "var(--shadow-sm)"
    }}>
      <h2 style={{ margin: "0 0 1rem", fontSize: "1.5rem", fontWeight: 700 }}>Welcome to Hiron! 👋</h2>
      <p style={{ margin: "0 0 2rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
        Your intelligent recruiting platform is ready. Follow these steps to get started and let AI streamline your hiring process.
      </p>
      
      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", alignItems: "flex-start", textAlign: "left", marginBottom: "2.5rem" }}>
        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <div style={{ width: "32px", height: "32px", borderRadius: "50%", backgroundColor: "var(--color-primary)", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700 }}>1</div>
          <div>
            <strong style={{ display: "block", color: "var(--text-primary)" }}>Create your first job</strong>
            <span style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>Define the role, skills, and pipeline stages.</span>
          </div>
        </div>
        
        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <div style={{ width: "32px", height: "32px", borderRadius: "50%", backgroundColor: "var(--bg-subtle)", color: "var(--text-muted)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700 }}>2</div>
          <div>
            <strong style={{ display: "block", color: "var(--text-primary)" }}>Upload resumes</strong>
            <span style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>Drop PDFs to automatically extract skills and experience.</span>
          </div>
        </div>
        
        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <div style={{ width: "32px", height: "32px", borderRadius: "50%", backgroundColor: "var(--bg-subtle)", color: "var(--text-muted)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700 }}>3</div>
          <div>
            <strong style={{ display: "block", color: "var(--text-primary)" }}>Let AI score candidates</strong>
            <span style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>See who fits best based on deep semantic matching.</span>
          </div>
        </div>
      </div>
      
      <Link href="/jobs/new" style={{ textDecoration: "none" }}>
        <Button variant="primary">Create First Job</Button>
      </Link>
    </div>
  );
}
