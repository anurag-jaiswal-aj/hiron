"use client";

import React from "react";
import { Badge } from "../ui/Badge";

interface UserStatusBadgeProps {
  isActive: boolean;
}

export function UserStatusBadge({ isActive }: UserStatusBadgeProps): React.ReactElement {
  return (
    <Badge variant={isActive ? "active" : "muted"}>
      {isActive ? "Active" : "Inactive"}
    </Badge>
  );
}
