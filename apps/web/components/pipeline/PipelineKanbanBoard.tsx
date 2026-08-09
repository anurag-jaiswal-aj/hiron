import React, { useEffect, useState, useCallback } from "react";
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  KeyboardSensor,
} from "@dnd-kit/core";
import { sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import { pipelineApi, PipelineStageStats, KanbanCandidateCard as KanbanCandidateCardType } from "../../lib/pipeline-api";
import { KanbanColumn } from "./KanbanColumn";
import { KanbanCandidateCard } from "./KanbanCandidateCard";
import { CandidateActionModal } from "./CandidateActionModal";

interface PipelineKanbanBoardProps {
  jobId: string;
  canManage: boolean;
}

export function PipelineKanbanBoard({ jobId, canManage }: PipelineKanbanBoardProps): React.ReactElement {
  const [stages, setStages] = useState<PipelineStageStats[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // For Drag Overlay
  const [activeCandidate, setActiveCandidate] = useState<KanbanCandidateCardType | null>(null);

  // For Candidate Actions
  const [selectedCandidate, setSelectedCandidate] = useState<KanbanCandidateCardType | null>(null);

  // For Mobile View
  const [isMobile, setIsMobile] = useState(false);
  const [activeMobileStageId, setActiveMobileStageId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5, // 5px drag distance to activate, allows clicking without dragging
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const fetchBoard = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const response = await pipelineApi.getPipelineBoard(jobId);
      setStages(response.data);
      if (response.data.length > 0 && !activeMobileStageId) {
        setActiveMobileStageId(response.data[0].stageId);
      }
    } catch (err: unknown) {
      setErrorMsg((err as Error).message || "Failed to load pipeline board");
    } finally {
      setIsLoading(false);
    }
  }, [jobId, activeMobileStageId]);

  useEffect(() => {
    fetchBoard();
    
    const checkMobile = (): void => {
      setIsMobile(window.innerWidth <= 768);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, [fetchBoard]);

  const handleDragStart = (event: DragStartEvent): void => {
    const { active } = event;
    const { candidate } = active.data.current as { candidate: KanbanCandidateCardType };
    setActiveCandidate(candidate);
  };

  const handleDragEnd = async (event: DragEndEvent): Promise<void> => {
    setActiveCandidate(null);
    if (!canManage) return;

    const { active, over } = event;
    if (!over) return;

    const activeId = active.id;
    const overId = over.id; // Either a column (stageId) or another card (jobCandidateId)

    // Find source and target stages
    let sourceStageId: string | null = null;
    let targetStageId: string | null = null;
    let candidateToMove: KanbanCandidateCardType | null = null;

    for (const stage of stages) {
      if (stage.candidates.some(c => c.jobCandidateId === activeId)) {
        sourceStageId = stage.stageId;
        candidateToMove = stage.candidates.find(c => c.jobCandidateId === activeId)!;
      }
      if (stage.stageId === overId) {
        targetStageId = stage.stageId;
      } else if (stage.candidates.some(c => c.jobCandidateId === overId)) {
        targetStageId = stage.stageId;
      }
    }

    if (!sourceStageId || !targetStageId || !candidateToMove) return;
    if (sourceStageId === targetStageId) return;

    // Optimistic UI Update
    const originalStages = [...stages];
    setStages(prev => {
      const newStages = prev.map(s => ({ ...s, candidates: [...s.candidates] }));
      const sStage = newStages.find(s => s.stageId === sourceStageId)!;
      const tStage = newStages.find(s => s.stageId === targetStageId)!;
      
      sStage.candidates = sStage.candidates.filter(c => c.jobCandidateId !== activeId);
      sStage.candidateCount = sStage.candidates.length;

      // Check if target is 'Rejected' (naively by name) to just push, or just push anyway
      tStage.candidates.push(candidateToMove!);
      tStage.candidateCount = tStage.candidates.length;
      
      return newStages;
    });

    try {
      await pipelineApi.moveCandidateStage(activeId as string, targetStageId);
    } catch (err: unknown) {
      // Revert
      setStages(originalStages);
      setErrorMsg((err as Error).message || "Failed to move candidate");
    }
  };

  if (isLoading) {
    return <div style={{ padding: "2rem", textAlign: "center" }}>Loading pipeline...</div>;
  }

  if (errorMsg) {
    return (
      <div style={{ padding: "2rem", color: "var(--text-danger)", textAlign: "center" }}>
        {errorMsg}
      </div>
    );
  }

  if (stages.length === 0) {
    return (
      <div style={{ padding: "4rem 2rem", textAlign: "center", color: "var(--text-secondary)" }}>
        No pipeline stages configured for this job.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%", position: "relative" }}>
      <h2 className="sr-only">Pipeline Kanban Board</h2>
      {isMobile && (
        <div style={{ padding: "1rem", backgroundColor: "var(--bg-surface-secondary)", borderBottom: "1px solid var(--border-subtle)" }}>
          <label htmlFor="mobileStageSelect" style={{ display: "block", fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.5rem" }}>
            Select Stage
          </label>
          <select 
            id="mobileStageSelect"
            value={activeMobileStageId || ""} 
            onChange={(e) => setActiveMobileStageId(e.target.value)}
            style={{ width: "100%", padding: "0.5rem", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}
          >
            {stages.map(stage => (
              <option key={stage.stageId} value={stage.stageId}>
                {stage.stageName} ({stage.candidateCount})
              </option>
            ))}
          </select>
        </div>
      )}

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div
          style={{
            display: "flex",
            gap: "1rem",
            padding: "1.5rem",
            overflowX: "auto",
            overflowY: "hidden",
            flexGrow: 1,
            height: "calc(100vh - 250px)", // Roughly remaining screen height
            minHeight: "500px",
          }}
        >
          {stages
            .filter(stage => !isMobile || stage.stageId === activeMobileStageId)
            .map((stage) => (
            <KanbanColumn
              key={stage.stageId}
              stage={stage}
              onCardClick={(candidate) => {
                setSelectedCandidate(candidate);
              }}
              canManage={canManage}
            />
          ))}
        </div>

        <DragOverlay>
          {activeCandidate ? <KanbanCandidateCard candidate={activeCandidate} /> : null}
        </DragOverlay>
      </DndContext>

      {selectedCandidate && (
        <CandidateActionModal
          isOpen={true}
          onClose={() => {
            setSelectedCandidate(null);
          }}
          candidate={selectedCandidate}
          jobId={jobId}
          canManage={canManage}
          onUpdated={fetchBoard}
        />
      )}
    </div>
  );
}
