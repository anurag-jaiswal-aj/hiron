"use client";

import React from "react";
import { useEmbeddingStatus, EntityType } from "../../hooks/useEmbeddingStatus";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

interface EmbeddingStatusBadgeProps {
  entityType: EntityType;
  entityId: string;
}

export function EmbeddingStatusBadge({ entityType, entityId }: EmbeddingStatusBadgeProps): React.ReactElement {
  const { status, error, isPolling, canRegenerate, regenerate } = useEmbeddingStatus(entityType, entityId);

  if (error && !isPolling) {
    return (
      <Badge variant="error" title={`Failed to load embedding status. ${error.message}`}>
        ⚠️ Embedding Error
      </Badge>
    );
  }

  if (status === "loading") {
    return (
      <Badge variant="muted">
        Checking embedding...
      </Badge>
    );
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
      {status === "current" && (
        <Badge variant="active" style={{ backgroundColor: "#166534", color: "white", borderColor: "#14532d" }}>
          Embeddings Ready
        </Badge>
      )}

      {status === "stale" && (
        <Badge variant="warning" style={{ color: "#d97706", borderColor: "#d97706", backgroundColor: "transparent" }}>
          ⚠️ Embedding Stale
        </Badge>
      )}

      {status === "missing" && (
        <Badge variant="muted">
          ⚠️ No Embedding
        </Badge>
      )}

      {status === "queued" && (
        <Badge variant="active" style={{ backgroundColor: "var(--bg-app)" }}>
          ⏳ Generating...
        </Badge>
      )}

      {canRegenerate && status !== "current" && status !== "queued" && (
        <Button 
          type="button"
          variant="secondary" 
          size="sm" 
          onClick={regenerate}
          disabled={isPolling}
        >
          {isPolling ? "⏳ Generating..." : "🔄 Generate"}
        </Button>
      )}
    </div>
  );
}
