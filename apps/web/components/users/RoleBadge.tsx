"use client";

import React from "react";
import { Badge } from "../ui/Badge";

interface RoleBadgeProps {
  role: string;
}

const ROLE_LABELS: Record<string, string> = {
  org_admin: "Org Admin",
  recruiter: "Recruiter",
  hiring_manager: "Hiring Manager",
  read_only: "Read Only",
};

export function RoleBadge({ role }: RoleBadgeProps): React.ReactElement {
  const normalizedRole = role.toLowerCase();
  const label = ROLE_LABELS[normalizedRole] || role;

  return (
    <Badge variant={normalizedRole === "org_admin" ? "active" : "neutral"}>
      {label}
    </Badge>
  );
}
