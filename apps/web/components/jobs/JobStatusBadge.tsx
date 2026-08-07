import React from "react";
import { Badge } from "../ui/Badge";

interface JobStatusBadgeProps {
  status: string;
}

export function JobStatusBadge({ status }: JobStatusBadgeProps): React.ReactElement {
  const normalized = (status || "").toLowerCase();

  let label = status;
  let variant: "active" | "neutral" | "muted" = "neutral";

  switch (normalized) {
    case "open":
      label = "Open";
      variant = "active"; // white/neutral emphasis
      break;
    case "draft":
      label = "Draft";
      variant = "muted"; // muted gray
      break;
    case "paused":
      label = "Paused";
      variant = "neutral"; // neutral gray
      break;
    case "closed":
      label = "Closed";
      variant = "muted"; // darker muted gray
      break;
    case "archived":
      label = "Archived";
      variant = "muted";
      break;
  }

  return <Badge variant={variant}>{label}</Badge>;
}
