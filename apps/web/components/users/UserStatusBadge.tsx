"use client";

import React from "react";
import { Badge } from "../ui/Badge";

interface UserStatusBadgeProps {
  isActive: boolean;
  isEmailVerified?: boolean;
}

export function UserStatusBadge({
  isActive,
  isEmailVerified,
}: UserStatusBadgeProps): React.ReactElement {
  if (isEmailVerified === false) {
    return <Badge variant="warning">Pending</Badge>;
  }

  return <Badge variant={isActive ? "active" : "muted"}>{isActive ? "Active" : "Inactive"}</Badge>;
}
