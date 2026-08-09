import React from "react";
import { ActivityFeedItem } from "../../lib/dashboard-api";

interface Props {
  activities: ActivityFeedItem[];
}

export function RecentActivity({ activities }: Props): React.ReactElement {
  if (!activities || activities.length === 0) {
    return (
      <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)", border: "1px dashed var(--border-subtle)", borderRadius: "var(--radius-md)" }}>
        No recent activity.
      </div>
    );
  }

  const formatTimeAgo = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.round(diffMs / 60000);
    
    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins} min ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      {activities.map(activity => (
        <div key={activity.id} style={{ display: "flex", gap: "0.75rem", padding: "0.5rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
          <div style={{ 
            width: "32px", 
            height: "32px", 
            borderRadius: "50%", 
            backgroundColor: "var(--bg-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            fontSize: "0.875rem"
          }}>
            {activity.actorName ? activity.actorName.charAt(0).toUpperCase() : "🤖"}
          </div>
          <div>
            <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--text-primary)", lineHeight: 1.4 }}>
              <span style={{ fontWeight: 600 }}>{activity.actorName || "System"}</span> {activity.description}
            </p>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              {formatTimeAgo(activity.timestamp)}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
