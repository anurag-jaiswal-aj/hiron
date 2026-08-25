"use client";

import React, { useEffect, useRef } from "react";

/**
 * BackgroundGrid — Global interactive grid background for Hiron.
 *
 * Renders a subtle CSS grid with a cursor-following radial highlight.
 * Uses CSS custom properties + requestAnimationFrame for smooth,
 * render-free cursor tracking. Sits behind all content at z-0.
 */
export default function BackgroundGrid(): React.ReactElement {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    let mouseX = 0;
    let mouseY = 0;
    let currentX = 0;
    let currentY = 0;
    let rafId: number;

    const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

    const onMouseMove = (e: MouseEvent): void => {
      mouseX = e.clientX;
      mouseY = e.clientY;
    };

    const animate = (): void => {
      currentX = lerp(currentX, mouseX, 0.08);
      currentY = lerp(currentY, mouseY, 0.08);
      el.style.setProperty("--grid-x", `${currentX}px`);
      el.style.setProperty("--grid-y", `${currentY}px`);
      rafId = requestAnimationFrame(animate);
    };

    window.addEventListener("mousemove", onMouseMove, { passive: true });
    rafId = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      cancelAnimationFrame(rafId);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      aria-hidden="true"
      className="fixed inset-0 z-0 pointer-events-none"
      style={
        {
          "--grid-x": "50vw",
          "--grid-y": "50vh",
        } as React.CSSProperties
      }
    >
      {/* Base grid — always visible, very subtle */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)",
          backgroundSize: "4rem 4rem",
          backgroundPosition: "center top",
        }}
      />

      {/* Interactive highlight layer — follows the cursor */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.115) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.115) 1px, transparent 1px)",
          backgroundSize: "4rem 4rem",
          backgroundPosition: "center top",
          maskImage:
            "radial-gradient(circle 280px at var(--grid-x) var(--grid-y), black 0%, transparent 100%)",
          WebkitMaskImage:
            "radial-gradient(circle 280px at var(--grid-x) var(--grid-y), black 0%, transparent 100%)",
        }}
      />
    </div>
  );
}
