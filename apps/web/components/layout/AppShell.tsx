"use client";

import React from "react";
import { Sidebar } from "./Sidebar";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps): React.ReactElement {
  return (
    <div
      className="app-shell"
      style={{
        display: "flex",
        minHeight: "100vh",
        backgroundColor: "var(--bg-app)",
        color: "var(--text-primary)",
      }}
    >
      <Sidebar />
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          minWidth: 0,
        }}
      >
        <main
          className="main-content"
          style={{
            flex: 1,
            padding: "2rem 2.5rem",
            maxWidth: "1280px",
            width: "100%",
            margin: "0 auto",
          }}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
