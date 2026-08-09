import React from "react";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy, useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { KanbanCandidateCard } from "./KanbanCandidateCard";
import type { PipelineStageStats, KanbanCandidateCard as KanbanCandidateCardType } from "../../lib/pipeline-api";

interface SortableCardProps {
  id: string;
  candidate: KanbanCandidateCardType;
  onClick: () => void;
  canManage: boolean;
}

function SortableKanbanCard({ id, candidate, onClick, canManage }: SortableCardProps): React.ReactElement {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
    data: {
      type: "Candidate",
      candidate,
    },
    disabled: !canManage,
  });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    zIndex: isDragging ? 1 : 0,
    position: "relative",
  };

  return (
    <div 
      ref={setNodeRef} 
      style={style} 
      {...attributes} 
      {...(canManage ? listeners : {})} 
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick(); }}
    >
      <KanbanCandidateCard candidate={candidate} />
    </div>
  );
}

interface ColumnProps {
  stage: PipelineStageStats;
  onCardClick: (candidate: KanbanCandidateCardType, stageId: string) => void;
  canManage: boolean;
}

export function KanbanColumn({ stage, onCardClick, canManage }: ColumnProps): React.ReactElement {
  const { setNodeRef, isOver } = useDroppable({
    id: stage.stageId,
    data: {
      type: "Column",
      stage,
    },
  });

  const candidateIds = stage.candidates.map((c) => c.jobCandidateId);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        minWidth: "280px",
        maxWidth: "280px",
        backgroundColor: "var(--bg-surface-secondary)",
        borderRadius: "var(--radius-lg)",
        flexShrink: 0,
        height: "100%",
        maxHeight: "100%",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "1rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <h3 style={{ fontSize: "0.875rem", fontWeight: 600, margin: 0, color: "var(--text-primary)" }}>
          {stage.stageName}
        </h3>
        <span
          style={{
            backgroundColor: "var(--bg-surface)",
            color: "var(--text-secondary)",
            fontSize: "0.75rem",
            fontWeight: 600,
            padding: "0.125rem 0.5rem",
            borderRadius: "var(--radius-full)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          {stage.candidates.length}
        </span>
      </div>

      <div
        ref={setNodeRef}
        style={{
          padding: "0.75rem",
          flexGrow: 1,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: "0.5rem",
          backgroundColor: isOver ? "var(--bg-surface-hover)" : "transparent",
          transition: "background-color 0.2s ease",
          minHeight: "100px",
        }}
      >
        <SortableContext items={candidateIds} strategy={verticalListSortingStrategy}>
          {stage.candidates.map((candidate) => (
            <SortableKanbanCard
              key={candidate.jobCandidateId}
              id={candidate.jobCandidateId}
              candidate={candidate}
              onClick={() => onCardClick(candidate, stage.stageId)}
              canManage={canManage}
            />
          ))}
        </SortableContext>
        {stage.candidates.length === 0 && (
          <div style={{ textAlign: "center", padding: "2rem 1rem", color: "var(--text-muted)", fontSize: "0.875rem" }}>
            No candidates
          </div>
        )}
      </div>
    </div>
  );
}
