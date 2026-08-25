"use client";
import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";

export function HironExperience(): React.ReactElement {
  const [activeStage, setActiveStage] = useState(0);

  const stage0Ref = useRef<HTMLDivElement>(null);
  const stage1Ref = useRef<HTMLDivElement>(null);
  const stage2Ref = useRef<HTMLDivElement>(null);
  const stage3Ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const index = Number(entry.target.getAttribute("data-stage"));
            setActiveStage(index);
          }
        });
      },
      { rootMargin: "-40% 0px -40% 0px", threshold: 0 }
    );

    if (stage0Ref.current) observer.observe(stage0Ref.current);
    if (stage1Ref.current) observer.observe(stage1Ref.current);
    if (stage2Ref.current) observer.observe(stage2Ref.current);
    if (stage3Ref.current) observer.observe(stage3Ref.current);

    return () => observer.disconnect();
  }, []);

  const narratives = [
    {
      title: "HIRON",
      heading: "Hiring, without the operational mess.",
      desc: "Jobs → candidates → decisions.",
      cta: true
    },
    {
      title: "ONE WORKSPACE",
      heading: "Every candidate, every stage, one system.",
      desc: ""
    },
    {
      title: "STRUCTURED DATA",
      heading: "Turn resumes into usable candidate profiles.",
      desc: ""
    },
    {
      title: "DECISIONS",
      heading: "Evaluate candidates and move the right people forward.",
      desc: ""
    }
  ];

  return (
    <section className="hiron-experience-container" style={{ display: "flex", backgroundColor: "var(--bg-app)", minHeight: "100vh" }}>

      {/* Left Narrative (Sticky on Desktop) */}
      <div className="narrative-rail" style={{
        flex: "0 0 35%",
        position: "relative",
        padding: "0 4rem"
      }}>
        <div style={{ position: "sticky", top: "0", height: "100vh", display: "flex", flexDirection: "column", justifyContent: "center" }}>

          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", letterSpacing: "0.05em" }}>
              {narratives[activeStage].title}
            </div>
            <h1 style={{ fontSize: "clamp(2rem, 4vw, 3.5rem)", fontWeight: 600, color: "var(--text-primary)", lineHeight: 1.1, letterSpacing: "-0.04em" }}>
              {narratives[activeStage].heading}
            </h1>
            {narratives[activeStage].desc && (
              <p style={{ fontSize: "1.125rem", color: "var(--text-secondary)", fontWeight: 400 }}>
                {narratives[activeStage].desc}
              </p>
            )}

            {narratives[activeStage].cta && (
              <div style={{ marginTop: "2rem" }}>
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
            )}
          </div>

        </div>
      </div>

      {/* Right Product Canvas (Natural Scroll) */}
      <div className="product-canvas" style={{ flex: "0 0 65%", display: "flex", flexDirection: "column", gap: "12rem", padding: "8rem 0 12rem 0" }}>

        {/* Stage 0: The Job */}
        <div ref={stage0Ref} data-stage="0" className="product-stage">
          {/* Mobile narrative injected here */}
          <div className="mobile-narrative">
            <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>HIRON</div>
            <h1 style={{ fontSize: "2rem", fontWeight: 600, color: "var(--text-primary)", lineHeight: 1.1, letterSpacing: "-0.04em", marginBottom: "2rem" }}>Hiring, without the operational mess.</h1>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
            <div style={{ borderBottom: "1px solid var(--border-subtle)", paddingBottom: "1.5rem" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600, marginBottom: "0.5rem" }}>JOB</div>
              <div style={{ fontSize: "2rem", fontWeight: 600, color: "var(--text-primary)" }}>Senior Backend Engineer</div>
            </div>

            <div style={{ display: "flex", flexDirection: "column" }}>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "1rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
                <span style={{ fontSize: "0.9375rem", color: "var(--text-secondary)", fontWeight: 500 }}>Applications</span>
                <span style={{ fontSize: "1rem", color: "var(--text-primary)", fontWeight: 600 }}>128</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "1rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
                <span style={{ fontSize: "0.9375rem", color: "var(--text-secondary)", fontWeight: 500 }}>Shortlisted</span>
                <span style={{ fontSize: "1rem", color: "var(--text-primary)", fontWeight: 600 }}>17</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "1rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
                <span style={{ fontSize: "0.9375rem", color: "var(--text-secondary)", fontWeight: 500 }}>Screening</span>
                <span style={{ fontSize: "1rem", color: "var(--text-primary)", fontWeight: 600 }}>8</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "1rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
                <span style={{ fontSize: "0.9375rem", color: "var(--text-secondary)", fontWeight: 500 }}>Interviews</span>
                <span style={{ fontSize: "1rem", color: "var(--text-primary)", fontWeight: 600 }}>4</span>
              </div>
            </div>
          </div>
        </div>

        {/* Stage 1: The Workspace (Candidate List) */}
        <div ref={stage1Ref} data-stage="1" className="product-stage">
          <div className="mobile-narrative">
            <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>ONE WORKSPACE</div>
            <h2 style={{ fontSize: "1.75rem", fontWeight: 600, color: "var(--text-primary)", lineHeight: 1.1, letterSpacing: "-0.04em", marginBottom: "2rem" }}>Every candidate, every stage, one system.</h2>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "1rem", paddingRight: "4rem" }}>
            {/* Real CandidateSearchResultCard analog */}
            {[
              { name: "Sarah Jenkins", role: "Product Manager", score: "92", stage: "Interview", active: false },
              { name: "David Kim", role: "Backend Engineer", score: "94", stage: "Screening", active: true },
              { name: "Alex Chen", role: "Frontend Developer", score: "81", stage: "Applied", active: false }
            ].map((c, i) => (
              <div key={i} style={{
                display: "flex",
                alignItems: "center",
                gap: "1.5rem",
                padding: "1.25rem",
                backgroundColor: c.active ? "var(--bg-hover)" : "var(--bg-surface)",
                border: c.active ? "1px solid var(--border-strong)" : "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-lg)"
              }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", width: "3.5rem", height: "3.5rem", borderRadius: "50%", border: "2px solid var(--border-strong)", color: "var(--text-primary)" }}>
                  <span style={{ fontSize: "1rem", fontWeight: 700 }}>{c.score}%</span>
                </div>
                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                  <span style={{ fontSize: "1.125rem", fontWeight: 600, color: "var(--text-primary)" }}>{c.name}</span>
                  <span style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>{c.role}</span>
                </div>
                <div style={{ padding: "0.1875rem 0.5rem", borderRadius: "var(--radius-sm)", fontSize: "0.75rem", fontWeight: 600, backgroundColor: "var(--bg-surface-secondary)", color: "var(--text-secondary)", border: "1px solid var(--border-subtle)" }}>
                  {c.stage}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Stage 2: Structured Data (David Kim Profile) */}
        <div ref={stage2Ref} data-stage="2" className="product-stage">
          <div className="mobile-narrative">
            <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>STRUCTURED DATA</div>
            <h2 style={{ fontSize: "1.75rem", fontWeight: 600, color: "var(--text-primary)", lineHeight: 1.1, letterSpacing: "-0.04em", marginBottom: "2rem" }}>Turn resumes into usable candidate profiles.</h2>
          </div>

          <div style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-strong)",
            borderRadius: "var(--radius-md)",
            padding: "2.5rem",
            marginRight: "4rem"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "2.5rem", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "1.5rem" }}>
              <div>
                <h3 style={{ fontSize: "1.5rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.25rem" }}>David Kim</h3>
                <span style={{ fontSize: "1rem", color: "var(--text-secondary)" }}>Backend Engineer</span>
              </div>
              <div style={{ padding: "0.25rem 0.75rem", borderRadius: "var(--radius-sm)", fontSize: "0.75rem", fontWeight: 600, backgroundColor: "var(--bg-hover)", color: "var(--text-primary)", border: "1px solid var(--border-strong)" }}>
                Active Match
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "1.5rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "0.875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>Experience</span>
                <span style={{ fontSize: "0.9375rem", color: "var(--text-primary)", fontWeight: 500 }}>5 Years</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "0.875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>Education</span>
                <span style={{ fontSize: "0.9375rem", color: "var(--text-primary)", fontWeight: 500 }}>B.S. Computer Science</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", paddingTop: "1rem", borderTop: "1px solid var(--border-subtle)" }}>
                <span style={{ fontSize: "0.875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>Extracted Skills</span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                  {["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"].map(skill => (
                    <span key={skill} style={{ padding: "0.25rem 0.75rem", borderRadius: "var(--radius-full)", backgroundColor: "var(--bg-app)", border: "1px solid var(--border-subtle)", fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Stage 3: Decisions (Score Breakdown) */}
        <div ref={stage3Ref} data-stage="3" className="product-stage">
          <div className="mobile-narrative">
            <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>DECISIONS</div>
            <h2 style={{ fontSize: "1.75rem", fontWeight: 600, color: "var(--text-primary)", lineHeight: 1.1, letterSpacing: "-0.04em", marginBottom: "2rem" }}>Evaluate candidates and move the right people forward.</h2>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "2rem", marginRight: "4rem" }}>
            <div style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              padding: "2rem"
            }}>
              <h3 style={{ fontSize: "1.125rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "1.5rem" }}>Score Breakdown</h3>

              <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
                {[
                  { label: "System Design", score: 80 },
                  { label: "Python / Backend", score: 100 },
                  { label: "Communication", score: 80 }
                ].map((s, i) => (
                  <div key={i} style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ fontSize: "0.875rem", fontWeight: 500, color: "var(--text-secondary)" }}>{s.label}</span>
                      <span style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)" }}>{s.score}/100</span>
                    </div>
                    <div style={{ width: "100%", height: "6px", backgroundColor: "var(--bg-app)", borderRadius: "99px", overflow: "hidden" }}>
                      <div style={{ width: `${s.score}%`, height: "100%", backgroundColor: s.score === 100 ? "#10B981" : "#F59E0B" }}></div>
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: "2rem", paddingTop: "1.5rem", borderTop: "1px solid var(--border-subtle)" }}>
                <p style={{ fontSize: "0.9375rem", color: "var(--text-secondary)", fontStyle: "italic", lineHeight: 1.5 }}>
                  &quot;Strong technical background. Demonstrated deep knowledge of Postgres internals.&quot;
                </p>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
              <div style={{ display: "inline-flex", alignItems: "center", padding: "0.75rem 1.5rem", borderRadius: "var(--radius-full)", backgroundColor: "var(--bg-hover)", border: "1px solid var(--border-strong)" }}>
                <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Move to Offer</span>
              </div>
            </div>
          </div>
        </div>

      </div>

      <style dangerouslySetInnerHTML={{__html: `
        .mobile-narrative { display: none; }
        @media (max-width: 900px) {
          .hiron-experience-container { flex-direction: column !important; }
          .narrative-rail { display: none !important; }
          .product-canvas { flex: 1 !important; padding: 4rem 2rem !important; gap: 6rem !important; }
          .mobile-narrative { display: block; margin-bottom: 2rem; }
          .product-stage { margin-right: 0 !important; }
          .product-canvas > div > div { margin-right: 0 !important; }
        }
      `}} />
    </section>
  );
}
