"use client";
import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";

const STEPS = [
  "JOB",
  "APPLICATIONS",
  "PARSING",
  "MATCH",
  "SCREENING",
  "EVALUATION",
  "DECISION",
  "OFFER"
];

const STAGE_CONTENT = [
  {
    title: "Start with the role.",
    desc: "Define the role once. Hiron turns your requirements into the foundation for everything that follows.",
  },
  {
    title: "Candidates, organized from the start.",
    desc: "Every application enters the same workflow, ready for review and action.",
  },
  {
    title: "Documents become data.",
    desc: "Resumes are automatically parsed into verified, structured candidate profiles.",
  },
  {
    title: "Find the candidates who fit.",
    desc: "The system instantly measures the structured profile against your exact job requirements.",
  },
  {
    title: "Screen candidates with AI.",
    desc: "Candidates flow seamlessly through the pipeline stages.",
  },
  {
    title: "Evaluate against what matters.",
    desc: "Objective, structured scoring tied directly to the job requirements.",
  },
  {
    title: "Make the decision.",
    desc: "All signals, parsing, and scoring converge into one final recommendation.",
  },
  {
    title: "Make the offer.",
    desc: "Turn the hiring decision into a ready-to-send offer.",
  }
];

export function ProductNarrative(): React.ReactElement {
  const [scrollProgressState, setScrollProgressState] = useState(0);
  const overrideProgressRef = useRef<number | null>(null);

  const containerRef = useRef<HTMLElement>(null);
  const heroRef = useRef<HTMLElement>(null);

  const setActiveStep = (index: number) => {
    overrideProgressRef.current = index;
    setScrollProgressState(index);
  };

  useEffect(() => {
    let rafId: number | null = null;
    let lastKnownPhysical = 0;

    const handleScroll = () => {
      if (rafId !== null) return;

      rafId = requestAnimationFrame(() => {
        rafId = null;

        const journey = containerRef.current;
        if (!journey) return;

        const rect = journey.getBoundingClientRect();
        const journeyTop = rect.top + window.scrollY;

        const isMobile = window.innerWidth < 768;
        const stickyOffset = isMobile ? 96 : 128;

        const scrollIntoJourney = window.scrollY - (journeyTop - stickyOffset);

        let physicalProgress = 0;
        if (scrollIntoJourney > 0) {
          physicalProgress = Math.min(
            STEPS.length - 1,
            Math.max(0, scrollIntoJourney / window.innerHeight)
          );
        }

        // If physical progress changed meaningfully, the user actually scrolled.
        // Release the override so scroll natively takes over again.
        if (Math.abs(lastKnownPhysical - physicalProgress) > 0.005) {
          overrideProgressRef.current = null;
        }
        lastKnownPhysical = physicalProgress;

        const activeProgress = overrideProgressRef.current !== null
          ? overrideProgressRef.current
          : physicalProgress;

        setScrollProgressState(activeProgress);
      });
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();

    return () => {
      window.removeEventListener("scroll", handleScroll);
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, []);

  const scrollToStart = () => {
    containerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  // Timeline switches exactly in the center of the visual transition (around 0.78)
  const getActiveTimelineStep = (progress: number) => {
    const base = Math.floor(progress);
    const remainder = progress - base;
    if (remainder > 0.78) {
      return Math.min(STEPS.length - 1, base + 1);
    }
    return base;
  };

  const activeDiscreteStep = getActiveTimelineStep(scrollProgressState);

  return (
    <div className="bg-[#0a0a0a] text-[#fafafa] min-h-screen font-sans selection:bg-white/10 overflow-x-clip">

      {/* HERO SECTION */}
      <section ref={heroRef} className="relative z-10 min-h-[calc(100svh-72px)] flex flex-col justify-center items-center text-center px-6 pt-12 pb-24">
        <div className="max-w-[800px] flex flex-col items-center mt-[-40px]">
          {/* Eyebrow */}
          <span className="text-[10px] md:text-[11px] font-bold tracking-[0.2em] text-[#a3a3a3] mb-7 md:mb-8 uppercase">
            The Hiring Workflow, Connected.
          </span>

          {/* Headline */}
          <h1 className="text-6xl md:text-7xl lg:text-[88px] xl:text-[96px] font-[650] md:font-bold tracking-tighter leading-[1.0] mb-7 md:mb-8 text-[#fafafa]">
            Hiring, without<br />
            <span className="text-[#a3a3a3]">the handoffs.</span>
          </h1>

          {/* Description */}
          <p className="text-[18px] md:text-[20px] text-[#8a8a8a] mb-9 md:mb-11 max-w-[700px] leading-relaxed">
            From the job you open to the offer you make, Hiron keeps every candidate, decision, and step connected.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <button
              onClick={scrollToStart}
              className="px-8 py-3.5 bg-[#fafafa] text-[#0a0a0a] rounded font-semibold text-[15px] transition-colors hover:bg-[#e5e5e5] min-h-[48px]"
            >
              Explore Hiron
            </button>
            <Link
              href="/login"
              className="px-8 py-3.5 border border-[#404040] bg-transparent text-[#fafafa] rounded font-semibold text-[15px] transition-colors hover:bg-[#111111] hover:border-[#525252] flex items-center gap-2 group min-h-[48px]"
            >
              Get started
              <span className="text-[#a3a3a3] group-hover:text-white transition-transform transform group-hover:translate-x-1">&rarr;</span>
            </Link>
          </div>
        </div>
      </section>

      {/* CONTINUOUS JOURNEY */}
      <section id="journey" ref={containerRef} className="relative z-10 max-w-[1280px] mx-auto px-6 pb-20">

        <div className="flex flex-col md:flex-row gap-12 relative items-start">

          {/* MOBILE TIMELINE */}
          <div className="md:hidden sticky top-0 z-50 w-full bg-[#0a0a0a]/90 backdrop-blur py-4 border-b border-[#262626]">
            <div className="text-xs font-semibold text-[#a3a3a3] tracking-widest mb-2">
              HIRON JOURNEY
            </div>
            <div className="h-1 w-full bg-[#262626] rounded-full overflow-hidden">
              <div
                className="h-full bg-[#fafafa]"
                style={{
                  width: `${(scrollProgressState / (STEPS.length - 1)) * 100}%`,
                  willChange: 'width'
                }}
              />
            </div>
            <div className="text-xs font-bold text-[#fafafa] tracking-widest">{STEPS[activeDiscreteStep]}</div>
          </div>

          {/* DESKTOP LEFT TIMELINE */}
          <aside className="hidden md:block w-64 shrink-0 sticky top-40 h-fit z-20">
            <div className="text-xs font-semibold text-[#8c8c8c] tracking-widest uppercase mb-8">
              Hiron Journey
            </div>
            <div className="relative ml-10 pt-[38px] flex flex-col gap-11">
              {/* Symmetrical Vertical Track */}
              <div className="absolute top-[48px] bottom-[10px] left-[0px] w-px bg-[#262626] pointer-events-none" />

              {/* Continuous Progress Line */}
              <div
                className="absolute top-[48px] left-[0px] w-px bg-[#fafafa] z-10 pointer-events-none"
                style={{
                  height: `calc(${(scrollProgressState / (STEPS.length - 1))} * calc(100% - 58px))`,
                  willChange: 'height'
                }}
              />

              {STEPS.map((step, i) => {
                const isActive = activeDiscreteStep === i;
                const isPast = activeDiscreteStep > i;
                const dotClassName = [
                  "absolute left-[-4px] top-1/2 -translate-y-1/2 w-2 h-2 rounded-full transition-all duration-500 z-20",
                  isActive
                    ? "bg-[#fafafa] shadow-[0_0_12px_rgba(250,250,250,0.4)]"
                    : isPast
                      ? "bg-[#fafafa]"
                      : "bg-[#262626] group-hover:bg-[#404040] group-focus-visible:bg-[#404040]"
                ].join(" ");

                const textClassName = [
                  "text-[13px] leading-none font-bold tracking-widest transition-colors duration-300",
                  isActive
                    ? "text-[#fafafa]"
                    : isPast
                      ? "text-[#a3a3a3] group-hover:text-[#fafafa] group-focus-visible:text-[#fafafa]"
                      : "text-[#404040] group-hover:text-[#a3a3a3] group-focus-visible:text-[#a3a3a3]"
                ].join(" ");

                return (
                  <button
                    key={step}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => setActiveStep(i)}
                    className="relative h-5 pl-8 transition-all duration-300 flex items-center text-left w-full group focus:outline-none focus-visible:outline-none"
                    aria-label={`Show ${step} stage`}
                  >
                    {/* Node Dot */}
                    <div className={dotClassName} />
                    <span className={textClassName}>
                      {step}
                    </span>
                  </button>
                );
              })}
            </div>
          </aside>

          {/* RIGHT COLUMN */}
          <div className="flex-1 w-full relative">

            {/* STICKY VIEWER */}
            <div className="sticky top-24 md:top-32 w-full h-[75vh] md:h-[70vh] z-10 flex flex-col pointer-events-auto">
              <JourneyStageViewer scrollProgress={scrollProgressState} />
            </div>

            {/* SCROLL TRACK (Invisible space to enable physical scrolling) */}
            {/* STEPS.length - 1 because we are already on step 0 when the journey section starts */}
            <div className="w-full" style={{ height: `${(STEPS.length - 1) * 100}vh` }} aria-hidden="true" />

          </div>
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="relative z-10 py-20 border-t border-[#262626] bg-[#0a0a0a] text-center px-6">
        <div className="max-w-[600px] mx-auto flex flex-col items-center">
          <div className="text-[11px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-6 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#fafafa]"></span>
            Hiring, Connected.
          </div>
          <h2 className="text-4xl md:text-5xl font-serif text-[#fafafa] mb-6 tracking-tight">One hiring workflow.<br />Start to finish.</h2>
          <p className="text-[15px] text-[#a3a3a3] mb-10 leading-relaxed">
            From the first candidate signal to the final offer, Hiron keeps every decision connected.
          </p>
          <Link href="/login" className="inline-flex items-center justify-center px-8 py-3.5 border border-transparent bg-[#fafafa] text-[#0a0a0a] rounded font-semibold text-[15px] transition-colors hover:bg-white min-h-[48px] gap-2 group">
            Get started
            <span className="text-[#404040] group-hover:text-[#0a0a0a] transition-colors">→</span>
          </Link>
        </div>
      </section>

      {/* MINIMAL FOOTER BOUNDARY */}
      <div className="w-full border-t border-[#262626] py-10 bg-[#0a0a0a] relative z-10 flex justify-center">
        <div className="text-[10px] font-bold text-[#404040] uppercase tracking-widest">© 2026 Hiron Intelligence</div>
      </div>

      {/* CSS animations (removed stageEnter as requested) */}
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes scan {
          0% { top: 10%; }
          50% { top: 90%; }
          100% { top: 10%; }
        }
      `}} />
    </div>
  );
}

function smoothstep(t: number) {
  return t * t * (3 - 2 * t);
}

function JourneyStageViewer({ scrollProgress }: { scrollProgress: number }): React.ReactElement {
  return (
    <div className="relative w-full h-full">
      {STAGE_CONTENT.map((content, index) => {
        const distance = scrollProgress - index;

        // Only render stages that are within fading distance (±1 step)
        if (Math.abs(distance) > 1.0) {
          return null;
        }

        let isFadingOut = false;
        let isFadingIn = false;
        let p = 0;

        if (distance >= 0 && distance <= 1) {
          isFadingOut = true;
          p = distance;
        } else if (distance < 0 && distance >= -1) {
          isFadingIn = true;
          p = distance + 1; // 0 to 1
        }

        // Base safety checks
        if (p >= 1.0 && isFadingOut) return null;
        if (p <= 0.0 && isFadingIn) return null;

        // Tracks (0 to 1 progress values)
        let tHeading = 0, tDesc = 0, tUI = 0;
        let opHeading = 0, opDesc = 0, opUI = 0;

        // Helper to calculate smoothed track progress
        const calcTrack = (start: number, end: number) => {
          if (p <= start) return 0;
          if (p >= end) return 1;
          return smoothstep((p - start) / (end - start));
        };

        if (isFadingOut) {
          // Exits: Text leaves first, UI lingers
          tHeading = calcTrack(0.62, 0.74);
          tDesc = calcTrack(0.65, 0.77);
          tUI = calcTrack(0.68, 0.80);

          opHeading = 1 - tHeading;
          opDesc = 1 - tDesc;
          opUI = 1 - tUI;
        } else if (isFadingIn) {
          // Enters: UI arrives first, Text follows
          tUI = calcTrack(0.76, 0.88);
          tHeading = calcTrack(0.80, 0.92);
          tDesc = calcTrack(0.84, 0.96);

          opHeading = tHeading;
          opDesc = tDesc;
          opUI = tUI;
        }

        if (opHeading === 0 && opDesc === 0 && opUI === 0) return null;

        // The transform values for hierarchical depth
        // OUT: moving from 0 to negative (t goes 0->1)
        // IN: moving from positive to 0 (t goes 0->1, so (1-t))
        const hY = isFadingOut ? -(tHeading * 16) : (1 - tHeading) * 16;
        const dY = isFadingOut ? -(tDesc * 10) : (1 - tDesc) * 10;
        const uY = isFadingOut ? -(tUI * 8) : (1 - tUI) * 8;

        const uScale = isFadingOut ? 1 - (tUI * 0.015) : 1 - ((1 - tUI) * 0.015);

        return (
          <div
            key={index}
            className="absolute inset-0 flex flex-col justify-center pointer-events-none"
          >
            {/* TEXT NARRATIVE */}
            <div className="mb-6 md:mb-10 max-w-xl">
              <h2
                className="font-semibold mb-3 text-[#fafafa] text-3xl md:text-5xl"
                style={{
                  opacity: opHeading,
                  transform: `translateY(${hY}px)`,
                  willChange: "opacity, transform"
                }}
              >
                {content.title}
              </h2>
              {true && (
                <p
                  className="text-base md:text-lg text-[#a3a3a3]"
                  style={{
                    opacity: opDesc,
                    transform: `translateY(${dY}px)`,
                    willChange: "opacity, transform"
                  }}
                >
                  {content.desc}
                </p>
              )}
            </div>

            {/* PRODUCT VISUALS */}
            {true && (
              <div
                className="flex-1 max-h-none md:max-h-[500px] w-full bg-[#111111] border border-[#262626] rounded-xl shadow-2xl flex flex-col relative overflow-x-hidden overflow-y-auto md:overflow-hidden pointer-events-auto custom-scrollbar"
                style={{
                  opacity: opUI,
                  transform: `translateY(${uY}px) scale(${uScale})`,
                  willChange: "opacity, transform"
                }}
              >
                {index === 0 && <JobStage />}
                {index === 1 && <ApplicationsStage />}
                {index === 2 && <ParsingStage />}
                {index === 3 && <MatchStage />}
                {index === 4 && <ScreeningStage />}
                {index === 5 && <EvaluationStage />}
                {index === 6 && <DecisionStage />}
                {index === 7 && <OfferStage />}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function JobStage(): React.ReactElement {
  return (
    <div className="w-full h-full flex flex-col">
      {/* Header */}
      <div className="px-6 py-5 border-b border-[#262626] flex justify-between items-center bg-[#0a0a0a]">
        <div className="flex items-center gap-3">
          <span className="text-[#a3a3a3] text-sm font-medium">Create job</span>
          <span className="text-[#404040]">/</span>
          <span className="text-emerald-400 text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 bg-emerald-500/10 rounded border border-emerald-500/20">Draft</span>
        </div>
        <button className="px-4 py-1.5 bg-[#fafafa] text-[#0a0a0a] text-sm font-semibold rounded hover:bg-white transition-colors">
          Save job
        </button>
      </div>

      <div className="px-6 py-6 md:py-12 space-y-8 flex-1 overflow-y-auto custom-scrollbar">
        {/* Title Area */}
        <div>
          <div className="text-[#fafafa] text-3xl font-bold mb-2 tracking-tight">Senior Backend Engineer</div>
          <div className="text-[#a3a3a3] text-sm">Build the role you&apos;re hiring for.</div>
        </div>

        {/* Job Details Grid */}
        <div>
          <div className="text-[10px] font-bold text-[#fafafa] uppercase tracking-widest mb-4 pb-2 border-b border-[#262626]">Job Details</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-y-4 gap-x-4">
            <div>
              <div className="text-[#8c8c8c] text-[11px] mb-1">Department</div>
              <div className="text-[#fafafa] text-sm font-medium">Engineering</div>
            </div>
            <div>
              <div className="text-[#8c8c8c] text-[11px] mb-1">Location</div>
              <div className="text-[#fafafa] text-sm font-medium">Bengaluru, India</div>
            </div>
            <div>
              <div className="text-[#8c8c8c] text-[11px] mb-1">Employment</div>
              <div className="text-[#fafafa] text-sm font-medium">Full-time</div>
            </div>
            <div>
              <div className="text-[#8c8c8c] text-[11px] mb-1">Experience</div>
              <div className="text-[#fafafa] text-sm font-medium">4–6 years</div>
            </div>
          </div>
        </div>

        {/* Required Skills */}
        <div>
          <div className="text-[10px] font-bold text-[#fafafa] uppercase tracking-widest mb-4 pb-2 border-b border-[#262626]">Required Skills</div>
          <div className="flex flex-wrap gap-2">
            {['Python', 'FastAPI', 'PostgreSQL', 'Docker', 'AWS', 'Redis', 'REST APIs'].map(skill => (
              <span key={skill} className="px-2.5 py-1 bg-[#171717] border border-[#262626] rounded text-xs text-[#fafafa]">{skill}</span>
            ))}
          </div>
        </div>

        {/* What we're looking for */}
        <div>
          <div className="text-[10px] font-bold text-[#fafafa] uppercase tracking-widest mb-4 pb-2 border-b border-[#262626]">What we&apos;re looking for</div>
          <div className="space-y-3">
            <div className="flex items-start gap-3 text-[#a3a3a3] text-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-[#525252] mt-1.5 flex-shrink-0"></span>
              <span>Build and maintain highly scalable backend services</span>
            </div>
            <div className="flex items-start gap-3 text-[#a3a3a3] text-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-[#525252] mt-1.5 flex-shrink-0"></span>
              <span>Design reliable, performant RESTful APIs</span>
            </div>
            <div className="flex items-start gap-3 text-[#a3a3a3] text-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-[#525252] mt-1.5 flex-shrink-0"></span>
              <span>Work closely with product and engineering teams to define features</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ApplicationsStage(): React.ReactElement {
  return (
    <div className="w-full h-full flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-[#262626] flex justify-between items-center bg-[#0a0a0a]">
        <div>
          <div className="text-[#a3a3a3] text-[11px] font-bold uppercase tracking-widest mb-1">Senior Backend Engineer</div>
          <div className="text-2xl font-bold text-[#fafafa] tracking-tight">Applications</div>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-[#8c8c8c] text-sm font-medium hidden md:inline">128 candidates</span>
          <button className="px-4 py-2 bg-[#fafafa] text-[#0a0a0a] text-xs font-bold rounded hover:bg-white transition-colors shadow-sm">
            + Add candidate
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="px-6 border-b border-[#262626] bg-[#0a0a0a] flex gap-8">
        <button className="py-3 text-xs font-bold text-[#fafafa] border-b-2 border-[#fafafa] tracking-wider uppercase">All <span className="ml-1.5 text-[#8c8c8c] font-medium">128</span></button>
        <button className="py-3 text-xs font-bold text-[#8c8c8c] hover:text-[#a3a3a3] tracking-wider uppercase">New <span className="ml-1.5 font-medium">24</span></button>
        <button className="py-3 text-xs font-bold text-[#8c8c8c] hover:text-[#a3a3a3] tracking-wider uppercase">Shortlisted <span className="ml-1.5 font-medium">17</span></button>
        <button className="py-3 text-xs font-bold text-[#8c8c8c] hover:text-[#a3a3a3] tracking-wider uppercase">Reviewing <span className="ml-1.5 font-medium">8</span></button>
      </div>

      <div className="flex-1 min-h-0 flex overflow-hidden bg-[#111111]">
        {/* Left: Candidate List */}
        <div className="hidden md:flex w-[60%] flex-col overflow-y-auto custom-scrollbar relative border-r border-[#262626]">
          {/* Row 1 (Selected) */}
          <div className="px-6 py-5 border-b border-[#262626] bg-[#171717] flex justify-between items-center group cursor-pointer relative flex-1">
            <div className="absolute left-0 top-0 bottom-0 w-1 bg-emerald-500"></div>
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-[#262626] flex items-center justify-center text-sm font-bold text-[#fafafa]">DK</div>
              <div>
                <div className="text-base font-bold text-[#fafafa]">David Kim</div>
                <div className="text-xs text-[#a3a3a3] mt-0.5">Backend Engineer</div>
                <div className="text-[11px] text-[#8c8c8c] mt-1.5">5 yrs • Python • FastAPI • PostgreSQL</div>
              </div>
            </div>
            <div className="flex flex-col items-end gap-2.5">
              <div className="text-[11px] text-[#8c8c8c]">Applied 12 min ago</div>
              <div className="px-2 py-1 bg-[#262626] text-[#fafafa] rounded text-[10px] font-bold tracking-widest uppercase border border-[#404040]">New</div>
            </div>
          </div>

          {/* Row 2 */}
          <div className="px-6 py-5 border-b border-[#262626] hover:bg-[#171717] transition-colors flex justify-between items-center group cursor-pointer flex-1">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-[#262626] flex items-center justify-center text-sm font-bold text-[#fafafa]">SC</div>
              <div>
                <div className="text-base font-bold text-[#fafafa] group-hover:text-[#fafafa] transition-colors">Sarah Chen</div>
                <div className="text-xs text-[#a3a3a3] mt-0.5">Backend Engineer</div>
                <div className="text-[11px] text-[#8c8c8c] mt-1.5">4 yrs • Python • PostgreSQL • Docker</div>
              </div>
            </div>
            <div className="flex flex-col items-end gap-2.5">
              <div className="text-[11px] text-[#8c8c8c]">Applied 28 min ago</div>
              <div className="px-2 py-1 bg-[#262626] text-[#fafafa] rounded text-[10px] font-bold tracking-widest uppercase border border-[#404040]">New</div>
            </div>
          </div>

          {/* Row 3 */}
          <div className="px-6 py-5 border-b border-[#262626] hover:bg-[#171717] transition-colors flex justify-between items-center group cursor-pointer opacity-90 flex-1">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-[#171717] border border-[#262626] flex items-center justify-center text-sm font-bold text-[#8c8c8c]">MR</div>
              <div>
                <div className="text-base font-bold text-[#fafafa] group-hover:text-[#fafafa] transition-colors">Michael Rao</div>
                <div className="text-xs text-[#a3a3a3] mt-0.5">Software Engineer</div>
                <div className="text-[11px] text-[#8c8c8c] mt-1.5">6 yrs • Python • AWS • Kubernetes</div>
              </div>
            </div>
            <div className="flex flex-col items-end gap-2.5">
              <div className="text-[11px] text-[#8c8c8c]">Applied 42 min ago</div>
              <div className="px-2 py-1 bg-[#171717] text-[#8c8c8c] rounded text-[10px] font-bold tracking-widest uppercase border border-[#262626]">Review</div>
            </div>
          </div>

          {/* Row 4 */}
          <div className="px-6 py-5 border-b border-[#262626] hover:bg-[#171717] transition-colors flex justify-between items-center group cursor-pointer opacity-80 flex-1">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-[#171717] border border-[#262626] flex items-center justify-center text-sm font-bold text-[#8c8c8c]">PS</div>
              <div>
                <div className="text-base font-bold text-[#fafafa] group-hover:text-[#fafafa] transition-colors">Priya Shah</div>
                <div className="text-xs text-[#a3a3a3] mt-0.5">Backend Engineer</div>
                <div className="text-[11px] text-[#8c8c8c] mt-1.5">5 yrs • Python • FastAPI • Redis</div>
              </div>
            </div>
            <div className="flex flex-col items-end gap-2.5">
              <div className="text-[11px] text-[#8c8c8c]">Applied 1 hr ago</div>
              <div className="px-2 py-1 bg-[#171717] text-[#8c8c8c] rounded text-[10px] font-bold tracking-widest uppercase border border-[#262626]">Shortlisted</div>
            </div>
          </div>
        </div>

        {/* Right: Selected Candidate Detail */}
        <div className="w-full md:w-[40%] bg-[#0a0a0a] flex flex-col px-6 py-5 pb-14 overflow-y-auto md:overflow-hidden md:border-l border-[#262626] relative">
          {/* Header */}
          <div className="text-[22px] font-bold text-[#fafafa] tracking-tight leading-tight">David Kim</div>
          <div className="text-[13px] text-[#a3a3a3] mt-0.5">Backend Engineer</div>
          <div className="text-xs text-[#8c8c8c] mt-1 mb-4">Bengaluru · 5 years experience</div>

          {/* Profile */}
          <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-1">Profile</div>
          <div className="text-[13px] text-[#fafafa] leading-snug mb-3">Senior backend engineer building API-driven systems and scalable data services.</div>

          {/* Experience */}
          <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-1">Experience</div>
          <div className="text-base text-[#fafafa] font-semibold leading-tight mb-3">5 years</div>

          {/* Skills */}
          <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-1.5">Skills</div>
          <div className="flex flex-wrap gap-1.5">
            <span className="px-2 py-0.5 bg-[#171717] border border-[#262626] rounded text-[11px] font-medium text-[#fafafa]">Python</span>
            <span className="px-2 py-0.5 bg-[#171717] border border-[#262626] rounded text-[11px] font-medium text-[#fafafa]">FastAPI</span>
            <span className="px-2 py-0.5 bg-[#171717] border border-[#262626] rounded text-[11px] font-medium text-[#fafafa]">PostgreSQL</span>
          </div>

          {/* CTA — pinned to bottom */}
          <div className="absolute bottom-0 left-0 right-0 px-5 py-3 bg-[#0a0a0a]">
            <button className="w-full py-2 flex justify-center items-center gap-2 text-[12px] font-bold text-[#fafafa] hover:text-white transition-colors group bg-[#111111] rounded border border-[#262626] hover:bg-[#171717]">
              Open candidate <span className="text-[#8c8c8c] group-hover:text-white transition-colors">→</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ParsingStage(): React.ReactElement {
  return (
    <div className="flex flex-col md:flex-row w-full h-full bg-[#0a0a0a]">
      {/* Left: Document Source (Resume Preview) */}
      <div className="w-full md:w-[37.5%] lg:w-[40%] bg-[#111111] border-b md:border-b-0 md:border-r border-[#262626] px-6 py-5 pb-6 relative overflow-hidden flex flex-col justify-between">
        <div className="flex flex-col h-full relative z-10">
          {/* File Metadata Header */}
          <div className="flex items-center justify-between mb-4 border-b border-[#262626] pb-3">
            <div>
              <div className="text-[11px] font-bold text-[#fafafa] flex items-center gap-2">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#8c8c8c]">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
                David_Kim_Resume.pdf
              </div>
              <div className="text-[10px] text-[#8c8c8c] mt-1 uppercase tracking-widest">Uploaded recently</div>
            </div>
          </div>

          {/* Minimalist Resume Document */}
          <div className="mb-4">
            <div className="text-xl font-serif text-[#fafafa] mb-0.5 tracking-tight">David Kim</div>
            <div className="text-xs text-[#a3a3a3] font-serif">Bengaluru, India • david.kim@example.com</div>
          </div>

          <div className="mb-4">
            <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-1.5 border-b border-[#262626] pb-1">Experience</div>
            <div className="mb-1.5">
              <div className="text-[13px] font-semibold text-[#fafafa] leading-snug">Senior Backend Engineer</div>
              <div className="text-[11px] text-[#a3a3a3] mb-1.5">Acme Corp • 2021 - Present</div>
              <div className="w-full h-1.5 bg-[#262626] rounded-full mb-1"></div>
              <div className="w-5/6 h-1.5 bg-[#262626] rounded-full mb-1"></div>
              <div className="w-full h-1.5 bg-[#262626] rounded-full mb-1"></div>
            </div>
          </div>

          <div className="mb-4">
            <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-1.5 border-b border-[#262626] pb-1">Skills</div>
            <div className="text-[12px] text-[#a3a3a3] leading-relaxed">
              Python, FastAPI, Django, Node.js, PostgreSQL, MongoDB, Redis, Docker, Kubernetes, AWS
            </div>
          </div>

          <div>
            <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-1.5 border-b border-[#262626] pb-1">Education</div>
            <div className="text-[13px] font-semibold text-[#fafafa] leading-snug">B.S. Computer Science</div>
            <div className="text-[11px] text-[#a3a3a3]">University of Technology • 2015 - 2019</div>
          </div>
        </div>

        {/* Scanning effect */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden z-20">
          <div className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-[#fafafa] to-transparent opacity-20 animate-scan shadow-[0_0_15px_rgba(255,255,255,0.1)]" />
        </div>
      </div>

      {/* Center: Processing Connection */}
      <div className="w-full py-12 md:py-0 md:w-[25%] lg:w-[20%] flex flex-col justify-center items-center relative overflow-hidden bg-[#0a0a0a]">

        {/* Verification pulse */}
        <div className="hidden md:block absolute left-0 right-0 top-1/2 h-[2px] bg-gradient-to-r from-transparent via-[#fafafa] to-transparent opacity-20 animate-scan shadow-[0_0_15px_rgba(255,255,255,0.1)]" />
        <div className="md:hidden absolute left-1/2 -translate-x-1/2 h-16 w-[2px] bg-gradient-to-b from-transparent via-[#fafafa] to-transparent opacity-30 animate-scan shadow-[0_0_15px_rgba(255,255,255,0.1)]" />

        {/* Connection Line */}
        <div className="hidden md:block absolute left-0 right-0 top-1/2 h-px bg-[#262626]" />
        <div className="md:hidden absolute top-0 bottom-0 left-1/2 w-px bg-[#262626]" />

        {/* Animated Extraction Text Tokens */}
        <div className="absolute left-0 right-0 top-1/2 h-px -translate-y-1/2 z-10 text-[9px] font-bold uppercase tracking-widest text-[#fafafa]">
          <div className="absolute top-1/2 -translate-y-1/2 animate-extract opacity-[0.55]">Python</div>
          <div className="absolute top-1/2 -translate-y-1/2 animate-extract opacity-[0.55]" style={{ animationDelay: '0.5s' }}>5 Years</div>
          <div className="absolute top-1/2 -translate-y-1/2 animate-extract opacity-[0.55]" style={{ animationDelay: '1.0s' }}>FastAPI</div>
          <div className="absolute top-1/2 -translate-y-1/2 animate-extract opacity-[0.55]" style={{ animationDelay: '1.5s' }}>Bengaluru</div>
        </div>

        {/* Processing animation label */}
        <div className="flex flex-col items-center gap-3 relative z-20 bg-[#0a0a0a] px-4 py-5 border border-[#262626] rounded-lg shadow-[0_0_20px_rgba(0,0,0,0.8)] w-4/5">
          <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest flex flex-col items-center gap-1.5">
            <div className="flex gap-1 mb-0.5">
              <div className="w-1 h-1 rounded-full bg-[#404040] animate-[pulse_1.5s_infinite]"></div>
              <div className="w-1 h-1 rounded-full bg-[#a3a3a3] animate-[pulse_1.5s_0.2s_infinite]"></div>
              <div className="w-1 h-1 rounded-full bg-[#fafafa] animate-[pulse_1.5s_0.4s_infinite]"></div>
            </div>
            AI Extraction
          </div>
        </div>

        {/* Subtle horizontal connecting lines */}
        <div className="absolute inset-0 pointer-events-none opacity-[0.05]"
             style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,1) 1px, transparent 1px)', backgroundSize: '100% 24px' }} />
      </div>

      {/* Right: Structured Output */}
      <div className="w-full md:w-[37.5%] lg:w-[40%] bg-[#0a0a0a] border-t md:border-t-0 md:border-l border-[#262626] px-6 py-5 pb-6 flex flex-col justify-between">
        <div className="flex flex-col w-full">
          <div className="flex flex-col mb-5 pb-4 border-b border-[#262626]">
            <div className="flex items-start justify-between mb-3">
              <div className="text-[11px] font-bold text-[#fafafa] uppercase tracking-widest flex items-center gap-2 mt-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#fafafa] animate-pulse shadow-[0_0_8px_rgba(255,255,255,0.4)]"></span>
                Structured Profile
              </div>
              <div className="flex flex-col items-end gap-1">
                <div className="text-[9px] font-bold text-[#8c8c8c] uppercase tracking-widest">AI Extraction</div>
                <div className="px-1.5 py-0.5 bg-[#171717] border border-[#262626] text-[#fafafa] text-[9px] font-bold rounded uppercase tracking-wider">
                  98% Confidence
                </div>
              </div>
            </div>

            {/* AI Summary */}
            <div className="text-[11px] text-[#a3a3a3] leading-relaxed">
              Strong backend candidate with deep expertise in API design and scalable data architecture. Ready for technical screening.
            </div>
          </div>

          <div className="flex flex-col gap-4">
            <div>
              <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-1">Extracted Role & Experience</div>
              <div className="flex items-end gap-3 mt-1">
                <div className="text-[14px] text-[#fafafa] font-bold leading-tight">Backend Engineer</div>
                <div className="text-[12px] text-[#a3a3a3] font-medium leading-tight mb-[1px]">5 years</div>
              </div>
            </div>

            <div>
              <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-1.5">Verified Skills</div>
              <div className="flex flex-wrap gap-1">
                <span className="px-2 py-0.5 bg-[#171717] border border-[#262626] rounded text-[10px] font-medium text-[#fafafa]">Python</span>
                <span className="px-2 py-0.5 bg-[#171717] border border-[#262626] rounded text-[10px] font-medium text-[#fafafa]">FastAPI</span>
                <span className="px-2 py-0.5 bg-[#171717] border border-[#262626] rounded text-[10px] font-medium text-[#fafafa]">PostgreSQL</span>
                <span className="px-2 py-0.5 bg-[#171717] border border-[#262626] rounded text-[10px] font-medium text-[#fafafa]">Docker</span>
                <span className="px-2 py-0.5 bg-[#171717] border border-[#262626] rounded text-[10px] font-medium text-[#fafafa]">AWS</span>
              </div>
            </div>
          </div>
        </div>

        {/* AI Match Readiness */}
        <div className="mt-4 pt-4 border-t border-[#262626] flex items-center justify-between">
          <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest">
            Ready for match analysis
          </div>
        </div>
      </div>
    </div>
  );
}

function MatchStage(): React.ReactElement {
  return (
    <div className="flex flex-col md:flex-row w-full h-full bg-[#0a0a0a]">
      {/* Left: Job Requirements */}
      <div className="w-full md:w-[37.5%] lg:w-[40%] bg-[#111111] border-b md:border-b-0 md:border-r border-[#262626] p-6 relative overflow-hidden flex flex-col justify-between">
        <div className="flex flex-col relative z-10">
          <div className="text-[11px] font-bold text-[#fafafa] uppercase tracking-widest mb-6 pb-4 border-b border-[#262626] flex items-center gap-2">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#8c8c8c]">
              <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
              <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
            </svg>
            Job Requirement Definition
          </div>

          <div className="mb-6">
            <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-1">Target Role</div>
            <div className="text-xl font-serif text-[#fafafa] tracking-tight">Senior Backend Engineer</div>
          </div>

          <div className="mb-6">
            <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-2">Required Experience</div>
            <div className="text-[13px] text-[#fafafa] font-medium">5+ years</div>
          </div>

          <div className="mb-6">
            <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-2 border-b border-[#262626] pb-1">Core Skills Required</div>
            <div className="flex flex-wrap gap-1.5 mt-2">
              <span className="px-2 py-0.5 bg-[#171717] border border-[#262626] rounded text-[11px] font-medium text-[#fafafa]">Python</span>
              <span className="px-2 py-0.5 bg-[#171717] border border-[#262626] rounded text-[11px] font-medium text-[#fafafa]">FastAPI</span>
              <span className="px-2 py-0.5 bg-[#171717] border border-[#262626] rounded text-[11px] font-medium text-[#fafafa]">PostgreSQL</span>
              <span className="px-2 py-0.5 bg-[#171717] border border-[#262626] rounded text-[11px] font-medium text-[#fafafa]">AWS</span>
            </div>
          </div>

          <div>
            <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-1">Location</div>
            <div className="text-[13px] text-[#fafafa] font-medium">Bengaluru</div>
          </div>
        </div>
      </div>

      {/* Center: AI Match Engine */}
      <div className="w-full py-12 md:py-0 md:w-[25%] lg:w-[20%] flex flex-col justify-center items-center relative overflow-hidden bg-[#0a0a0a]">

        {/* Animated Connecting Lines */}
        <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
           {/* Center connections */}
           <div className="hidden md:block absolute left-0 right-0 h-px bg-[#262626]" />
           <div className="md:hidden absolute top-0 bottom-0 left-1/2 w-px bg-[#262626]" />

           {/* Flow pulses */}
           <div className="hidden md:block absolute w-full h-px overflow-hidden">
             <div className="w-1/3 h-full bg-gradient-to-r from-transparent via-[#fafafa] to-transparent opacity-20 animate-extract" />
           </div>
           <div className="md:hidden absolute h-full w-px left-1/2 -translate-x-1/2 overflow-hidden">
             <div className="h-1/3 w-full bg-gradient-to-b from-transparent via-[#fafafa] to-transparent opacity-20 animate-extract-vertical" />
           </div>
        </div>

        {/* Animated Requirement Tokens */}
        <div className="absolute left-0 right-0 top-1/2 h-px -translate-y-1/2 z-10 text-[9px] font-bold uppercase tracking-widest text-[#a3a3a3]">
          <div className="absolute top-1/2 -translate-y-1/2 animate-extract opacity-40">Python</div>
          <div className="absolute top-1/2 -translate-y-1/2 animate-extract opacity-40" style={{ animationDelay: '0.6s' }}>FastAPI</div>
          <div className="absolute top-1/2 -translate-y-1/2 animate-extract opacity-40" style={{ animationDelay: '1.2s' }}>5 Years</div>
          <div className="absolute top-1/2 -translate-y-1/2 animate-extract opacity-40" style={{ animationDelay: '1.8s' }}>Cloud</div>
        </div>

        <div className="flex flex-col items-center z-20 bg-[#0a0a0a] px-4 py-5 border border-[#262626] rounded-lg shadow-[0_0_20px_rgba(0,0,0,0.8)] w-4/5">
          <div className="flex flex-col gap-1 mb-4 opacity-50 w-full border-b border-[#262626] pb-3">
            <div className="text-[7px] font-bold text-[#fafafa] uppercase tracking-widest flex items-center gap-1.5"><span className="text-[#a3a3a3]">✓</span> Skills analyzed</div>
            <div className="text-[7px] font-bold text-[#fafafa] uppercase tracking-widest flex items-center gap-1.5"><span className="text-[#a3a3a3]">✓</span> Experience verified</div>
            <div className="text-[7px] font-bold text-[#fafafa] uppercase tracking-widest flex items-center gap-1.5"><span className="text-[#a3a3a3]">✓</span> Role alignment</div>
          </div>
          <div className="text-5xl font-bold text-[#fafafa] mb-2 tracking-tighter">94<span className="text-2xl text-[#8c8c8c]">%</span></div>
          <div className="text-[9px] font-bold text-[#8c8c8c] uppercase tracking-widest text-center mt-1 flex flex-col items-center gap-1.5">
            MATCH SCORE
            <span className="text-[#fafafa]">HIGH COMPATIBILITY</span>
          </div>
        </div>

        <div className="absolute bottom-6 text-[9px] font-bold text-[#404040] uppercase tracking-widest flex items-center gap-1.5">
          <span className="w-1 h-1 rounded-full bg-[#404040] animate-pulse"></span>
          AI Match Engine
        </div>

        {/* Subtle background grid/lines */}
        <div className="absolute inset-0 pointer-events-none opacity-[0.05]"
             style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,1) 1px, transparent 1px)', backgroundSize: '100% 24px' }} />
      </div>

      {/* Right: Candidate Fit */}
      <div className="w-full md:w-[37.5%] lg:w-[40%] bg-[#0a0a0a] border-t md:border-t-0 md:border-l border-[#262626] p-6 flex flex-col justify-between overflow-hidden relative">
        <div className="flex flex-col h-full relative z-10">
          <div className="flex items-center justify-between mb-5 pb-4 border-b border-[#262626]">
            <div className="text-[11px] font-bold text-[#fafafa] uppercase tracking-widest flex items-center gap-2">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#8c8c8c]">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
              </svg>
              AI Hiring Decision
            </div>
          </div>

          <div className="mb-5 flex justify-between items-start">
            <div>
              <div className="text-xl font-serif text-[#fafafa] tracking-tight mb-0.5">David Kim</div>
              <div className="text-[12px] text-[#a3a3a3]">Backend Engineer</div>
            </div>
          </div>

          <div className="mb-4">
            <div className="text-[10px] font-bold text-[#fafafa] uppercase tracking-widest mb-2 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-[#8c8c8c] rounded-full"></span>
              Why This Match
            </div>
            <ul className="text-[11px] text-[#a3a3a3] space-y-1.5 ml-3">
              <li className="flex items-start gap-1.5"><span className="text-[#fafafa]">•</span>Backend architecture alignment</li>
              <li className="flex items-start gap-1.5"><span className="text-[#fafafa]">•</span>API experience</li>
              <li className="flex items-start gap-1.5"><span className="text-[#fafafa]">•</span>Cloud systems</li>
            </ul>
          </div>

          <div className="mb-4">
            <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-2 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 border border-[#404040] rounded-full"></span>
              Potential Gap
            </div>
            <ul className="text-[11px] text-[#8c8c8c] space-y-1.5 ml-3">
              <li className="flex items-start gap-1.5"><span className="text-[#404040]">•</span>GraphQL exposure</li>
            </ul>
          </div>

          <div className="mt-auto pt-4 border-t border-[#262626]">
            <div className="text-[10px] font-bold uppercase tracking-widest flex items-center justify-between">
              <span className="text-[#8c8c8c]">Match Verified</span>
              <span className="text-[#fafafa] flex items-center gap-1">Ready for screening <span className="text-[14px]">→</span></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ScreeningStage(): React.ReactElement {
  return (
    <div className="flex flex-col md:flex-row w-full h-full bg-[#0a0a0a]">
      {/* Left: Candidate Interview Context */}
      <div className="w-full md:w-[37.5%] lg:w-[40%] bg-[#111111] border-b md:border-b-0 md:border-r border-[#262626] p-6 relative overflow-hidden flex flex-col justify-between">
        <div className="flex flex-col relative z-10">
          <div className="text-[11px] font-bold text-[#fafafa] uppercase tracking-widest mb-6 pb-4 border-b border-[#262626] flex items-center gap-2">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#8c8c8c]">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            Candidate Interview Context
          </div>

          <div className="mb-6 flex justify-between items-start">
            <div>
              <div className="text-xl font-serif text-[#fafafa] tracking-tight mb-0.5">David Kim</div>
              <div className="text-[12px] text-[#a3a3a3]">Backend Engineer</div>
            </div>
            <div className="px-2 py-1 bg-[#262626] text-[#fafafa] text-[9px] font-bold rounded uppercase tracking-wider border border-[#404040]">
              In Progress
            </div>
          </div>

          <div className="mb-6">
            <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-2 border-b border-[#262626] pb-1">Screening Session</div>
            <div className="flex flex-col gap-3 mt-3">
               <div className="flex items-start gap-2">
                 <div className="w-1.5 h-1.5 rounded-full bg-[#8c8c8c] mt-1.5 shrink-0"></div>
                 <div className="flex-1 text-[11px] text-[#a3a3a3] leading-relaxed">
                   <span className="text-[#fafafa] font-semibold">Q1:</span> Can you describe your experience designing APIs for high-throughput systems?
                 </div>
               </div>
               <div className="flex items-start gap-2">
                 <div className="w-1.5 h-1.5 rounded-full bg-[#8c8c8c] mt-1.5 shrink-0"></div>
                 <div className="flex-1 text-[11px] text-[#a3a3a3] leading-relaxed">
                   <span className="text-[#fafafa] font-semibold">Q2:</span> How do you handle database migrations with zero downtime?
                 </div>
               </div>
               <div className="flex items-start gap-2 opacity-50">
                 <div className="w-1.5 h-1.5 rounded-full bg-[#404040] mt-1.5 shrink-0 animate-pulse"></div>
                 <div className="flex-1 text-[11px] text-[#a3a3a3] leading-relaxed">
                   <span className="text-[#fafafa] font-semibold">Q3:</span> Generating technical question...
                 </div>
               </div>
            </div>
          </div>
        </div>
      </div>

      {/* Center: AI Screening Engine */}
      <div className="w-full py-12 md:py-0 md:w-[25%] lg:w-[20%] flex flex-col justify-center items-center relative overflow-hidden bg-[#0a0a0a]">

        {/* Animated Connecting Lines / Conversation flow */}
        <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
           {/* Center vertical flow */}
           <div className="absolute top-0 bottom-0 w-px bg-[#262626]" />

           {/* Flow pulses */}
           <div className="absolute h-full w-px overflow-hidden">
             <div className="h-1/3 w-full bg-gradient-to-b from-transparent via-[#fafafa] to-transparent opacity-20 animate-extract-vertical" />
           </div>
        </div>

        <div className="flex flex-col items-center z-20 bg-[#0a0a0a] px-4 py-5 border border-[#262626] rounded-lg shadow-[0_0_20px_rgba(0,0,0,0.8)] w-4/5 text-center">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#fafafa] mb-3 animate-pulse opacity-80">
            <path d="M12 2a10 10 0 1 0 10 10H12V2z"></path>
            <path d="M12 12 2.1 7.1"></path>
            <path d="M12 12l9.9 4.9"></path>
          </svg>
          <div className="text-[8px] font-bold text-[#fafafa] uppercase tracking-widest text-center flex flex-col items-center gap-1.5">
            EVALUATING
          </div>
        </div>

        {/* Evaluation Indicators */}
        <div className="relative mt-6 md:absolute md:inset-x-0 md:top-[60%] md:mt-4 flex flex-col items-center gap-2 z-10 w-full px-2">
          <div className="w-full px-2 py-1.5 bg-[#111111] border border-[#262626] rounded-full text-[7px] font-bold uppercase tracking-widest text-[#a3a3a3] shadow-md flex items-center justify-center gap-1.5">
            <span className="w-1 h-1 rounded-full bg-[#fafafa]"></span> Technical depth analyzed
          </div>
          <div className="w-full px-2 py-1.5 bg-[#111111] border border-[#262626] rounded-full text-[7px] font-bold uppercase tracking-widest text-[#a3a3a3] shadow-md flex items-center justify-center gap-1.5" style={{ animationDelay: '0.4s' }}>
            <span className="w-1 h-1 rounded-full bg-[#fafafa]"></span> Communication analyzed
          </div>
          <div className="w-full px-2 py-1.5 bg-[#111111] border border-[#262626] rounded-full text-[7px] font-bold uppercase tracking-widest text-[#404040] shadow-md flex items-center justify-center gap-1.5 opacity-50">
            <span className="w-1 h-1 rounded-full bg-[#404040] animate-pulse"></span> Problem solving analyzing
          </div>
        </div>

        <div className="absolute bottom-6 text-[9px] font-bold text-[#404040] uppercase tracking-widest flex items-center gap-1.5">
          <span className="w-1 h-1 rounded-full bg-[#404040] animate-pulse"></span>
          AI Screening Engine
        </div>

        {/* Subtle background grid/lines */}
        <div className="absolute inset-0 pointer-events-none opacity-[0.05]"
             style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,1) 1px, transparent 1px)', backgroundSize: '100% 24px' }} />
      </div>

      {/* Right: Screening Outcome */}
      <div className="w-full md:w-[37.5%] lg:w-[40%] bg-[#0a0a0a] border-t md:border-t-0 md:border-l border-[#262626] p-6 flex flex-col justify-between overflow-hidden relative">
        <div className="flex flex-col h-full relative z-10">
          <div className="flex items-center justify-between mb-5 pb-4 border-b border-[#262626]">
            <div className="text-[11px] font-bold text-[#fafafa] uppercase tracking-widest flex items-center gap-2">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#8c8c8c]">
                <polyline points="9 11 12 14 22 4"></polyline>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
              </svg>
              Screening Outcome
            </div>
            <div className="text-[9px] font-bold text-[#8c8c8c] uppercase tracking-widest flex items-center gap-1.5">
              SCREENING COMPLETE
            </div>
          </div>

          <div className="mb-4">
            <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-1 flex items-center gap-1.5">
              Screening Score
            </div>
            <div className="text-4xl font-bold text-[#fafafa] tracking-tighter flex items-end gap-2">
              87<span className="text-xl text-[#8c8c8c] mb-1">%</span>
            </div>
          </div>

          <div className="mb-4 grid grid-cols-2 gap-4">
            <div>
              <div className="text-[9px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-1.5">Strengths</div>
              <ul className="text-[11px] text-[#fafafa] space-y-1.5">
                <li className="flex gap-1.5 items-center"><span className="text-[#a3a3a3] text-[14px] leading-none">+</span>System Design</li>
                <li className="flex gap-1.5 items-center"><span className="text-[#a3a3a3] text-[14px] leading-none">+</span>Clear articulation</li>
              </ul>
            </div>
            <div>
              <div className="text-[9px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-1.5">Concerns</div>
              <ul className="text-[11px] text-[#8c8c8c] space-y-1.5">
                <li className="flex gap-1.5 items-center"><span className="text-[#404040] text-[14px] leading-none">-</span>Scaling limits</li>
              </ul>
            </div>
          </div>

          <div className="mt-auto pt-4 border-t border-[#262626]">
            <div className="text-[10px] font-bold uppercase tracking-widest flex items-center justify-between">
              <span className="text-[#8c8c8c]">Screening Verified</span>
              <span className="text-[#fafafa] flex items-center gap-1">Proceed to technical evaluation <span className="text-[14px]">→</span></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function EvaluationStage(): React.ReactElement {
  return (
    <div className="flex flex-col md:flex-row w-full h-full bg-[#0a0a0a]">
      {/* Left: Candidate Performance Evidence */}
      <div className="w-full md:w-[37.5%] lg:w-[40%] bg-[#111111] border-b md:border-b-0 md:border-r border-[#262626] p-6 relative overflow-hidden flex flex-col justify-between">
        <div className="flex flex-col relative z-10">
          <div className="text-[11px] font-bold text-[#fafafa] uppercase tracking-widest mb-6 pb-4 border-b border-[#262626] flex items-center gap-2">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#8c8c8c]">
              <path d="M12 20h9"></path>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>
            Performance Evidence
          </div>

          <div className="mb-6 flex justify-between items-start">
            <div>
              <div className="text-xl font-serif text-[#fafafa] tracking-tight mb-0.5">David Kim</div>
              <div className="text-[12px] text-[#a3a3a3]">Backend Engineer</div>
            </div>
          </div>

          <div className="mb-6">
            <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-3 border-b border-[#262626] pb-1">Evaluation Categories</div>

            <div className="space-y-4 mt-2">
              <div>
                <div className="flex justify-between text-[11px] mb-1.5"><span className="text-[#a3a3a3] font-semibold">Technical Score</span><span className="text-[#fafafa] font-bold">100/100</span></div>
                <div className="h-1 w-full bg-[#262626] rounded-full overflow-hidden"><div className="h-full bg-[#fafafa] w-[100%]" /></div>
              </div>
              <div>
                <div className="flex justify-between text-[11px] mb-1.5"><span className="text-[#a3a3a3] font-semibold">Communication Score</span><span className="text-[#fafafa] font-bold">80/100</span></div>
                <div className="h-1 w-full bg-[#262626] rounded-full overflow-hidden"><div className="h-full bg-[#8c8c8c] w-[80%]" /></div>
              </div>
              <div>
                <div className="flex justify-between text-[11px] mb-1.5"><span className="text-[#a3a3a3] font-semibold">Problem Solving Score</span><span className="text-[#fafafa] font-bold">90/100</span></div>
                <div className="h-1 w-full bg-[#262626] rounded-full overflow-hidden"><div className="h-full bg-[#fafafa] w-[90%] opacity-80" /></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Center: AI Evaluation Engine */}
      <div className="w-full py-12 md:py-0 md:w-[25%] lg:w-[20%] flex flex-col justify-center items-center relative overflow-hidden bg-[#0a0a0a]">

        {/* Animated Connecting Lines / Conversation flow */}
        <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
           {/* Center vertical flow */}
           <div className="absolute top-0 bottom-0 w-px bg-[#262626]" />

           {/* Flow pulses */}
           <div className="absolute h-full w-px overflow-hidden">
             <div className="h-1/3 w-full bg-gradient-to-b from-transparent via-[#fafafa] to-transparent opacity-20 animate-extract-vertical" />
           </div>
        </div>

        <div className="flex flex-col items-center z-20 bg-[#0a0a0a] px-4 py-5 border border-[#262626] rounded-lg shadow-[0_0_20px_rgba(0,0,0,0.8)] w-4/5 text-center">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#fafafa] mb-3 animate-pulse opacity-80">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
          </svg>
          <div className="text-[8px] font-bold text-[#fafafa] uppercase tracking-widest text-center flex flex-col items-center gap-1.5">
            ANALYZING
          </div>
        </div>

        {/* Evaluation Indicators */}
        <div className="relative mt-6 md:absolute md:inset-x-0 md:top-[60%] md:mt-4 flex flex-col items-center gap-2 z-10 w-full px-2">
          <div className="w-full px-2 py-1.5 bg-[#111111] border border-[#262626] rounded-full text-[7px] font-bold uppercase tracking-widest text-[#a3a3a3] shadow-md flex items-center justify-center gap-1.5">
            <span className="w-1 h-1 rounded-full bg-[#fafafa]"></span> Tech depth analyzed
          </div>
          <div className="w-full px-2 py-1.5 bg-[#111111] border border-[#262626] rounded-full text-[7px] font-bold uppercase tracking-widest text-[#a3a3a3] shadow-md flex items-center justify-center gap-1.5" style={{ animationDelay: '0.4s' }}>
            <span className="w-1 h-1 rounded-full bg-[#fafafa]"></span> Prob. solving analyzed
          </div>
          <div className="w-full px-2 py-1.5 bg-[#111111] border border-[#262626] rounded-full text-[7px] font-bold uppercase tracking-widest text-[#404040] shadow-md flex items-center justify-center gap-1.5 opacity-50">
            <span className="w-1 h-1 rounded-full bg-[#404040] animate-pulse"></span> Culture alignment
          </div>
        </div>

        <div className="absolute bottom-6 text-[9px] font-bold text-[#404040] uppercase tracking-widest flex items-center gap-1.5">
          <span className="w-1 h-1 rounded-full bg-[#404040] animate-pulse"></span>
          AI Evaluation Engine
        </div>

        {/* Subtle background grid/lines */}
        <div className="absolute inset-0 pointer-events-none opacity-[0.05]"
             style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,1) 1px, transparent 1px)', backgroundSize: '100% 24px' }} />
      </div>

      {/* Right: Evaluation Report */}
      <div className="w-full md:w-[37.5%] lg:w-[40%] bg-[#0a0a0a] border-t md:border-t-0 md:border-l border-[#262626] p-6 flex flex-col justify-between overflow-hidden relative">
        <div className="flex flex-col h-full relative z-10">
          <div className="flex items-center justify-between mb-5 pb-4 border-b border-[#262626]">
            <div className="text-[11px] font-bold text-[#fafafa] uppercase tracking-widest flex items-center gap-2">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#8c8c8c]">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
              </svg>
              Evaluation Report
            </div>
            <div className="text-[9px] font-bold text-[#8c8c8c] uppercase tracking-widest flex items-center gap-1.5">
              EVALUATION COMPLETE
            </div>
          </div>

          <div className="mb-4">
            <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-1 flex items-center gap-1.5">
              Overall Evaluation Score
            </div>
            <div className="text-4xl font-bold text-[#fafafa] tracking-tighter flex items-end gap-2">
              90<span className="text-xl text-[#8c8c8c] mb-1">%</span>
            </div>
          </div>

          <div className="mb-4 grid grid-cols-2 gap-4">
            <div>
              <div className="text-[9px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-1.5">Strengths</div>
              <ul className="text-[11px] text-[#fafafa] space-y-1.5">
                <li className="flex gap-1.5 items-center"><span className="text-[#a3a3a3] text-[14px] leading-none">+</span>Flawless backend knowledge</li>
                <li className="flex gap-1.5 items-center"><span className="text-[#a3a3a3] text-[14px] leading-none">+</span>Fast problem solving</li>
              </ul>
            </div>
            <div>
              <div className="text-[9px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-1.5">Improvement Areas</div>
              <ul className="text-[11px] text-[#8c8c8c] space-y-1.5">
                <li className="flex gap-1.5 items-center"><span className="text-[#404040] text-[14px] leading-none">-</span>Verbosity in answers</li>
              </ul>
            </div>
          </div>

          <div className="mt-auto pt-4 border-t border-[#262626]">
            <div className="text-[10px] font-bold uppercase tracking-widest flex items-center justify-between">
              <span className="text-[#8c8c8c]">Evaluation Verified</span>
              <span className="text-[#fafafa] flex items-center gap-1">Proceed to final decision <span className="text-[14px]">→</span></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function DecisionStage(): React.ReactElement {
  return (
    <div className="flex flex-col md:flex-row w-full h-full bg-[#0a0a0a]">
      {/* Left: Candidate Decision Summary */}
      <div className="w-full md:w-[37.5%] lg:w-[40%] bg-[#111111] border-b md:border-b-0 md:border-r border-[#262626] p-6 relative overflow-hidden flex flex-col justify-between">
        <div className="flex flex-col relative z-10">
          <div className="text-[11px] font-bold text-[#fafafa] uppercase tracking-widest mb-6 pb-4 border-b border-[#262626] flex items-center gap-2">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#8c8c8c]">
              <path d="M16 21v-2a4 4 0 0 0-4-4H5c-1.1 0-2 .9-2 2v2"></path>
              <circle cx="8.5" cy="7" r="4"></circle>
              <polyline points="17 11 19 13 23 9"></polyline>
            </svg>
            Decision Summary
          </div>

          <div className="mb-6 flex justify-between items-start">
            <div>
              <div className="text-xl font-serif text-[#fafafa] tracking-tight mb-0.5">David Kim</div>
              <div className="text-[12px] text-[#a3a3a3]">Backend Engineer</div>
            </div>
            <div className="px-2 py-1 bg-[#262626] text-[#fafafa] text-[9px] font-bold rounded uppercase tracking-wider border border-[#404040]">
              Cleared
            </div>
          </div>

          <div className="mb-6">
            <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-3 border-b border-[#262626] pb-1">Key Hiring Signals</div>
            <div className="space-y-2.5 mt-3">
              <div className="flex items-start gap-2">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#fafafa] shrink-0 mt-0.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
                <div className="flex-1 text-[11px] text-[#a3a3a3] leading-tight">
                  Requirements alignment verified
                </div>
              </div>
              <div className="flex items-start gap-2">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#fafafa] shrink-0 mt-0.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
                <div className="flex-1 text-[11px] text-[#a3a3a3] leading-tight">
                  Strong problem-solving evidence
                </div>
              </div>
              <div className="flex items-start gap-2">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#fafafa] shrink-0 mt-0.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
                <div className="flex-1 text-[11px] text-[#a3a3a3] leading-tight">
                  Low attrition risk profile
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Center: AI Decision Engine */}
      <div className="w-full py-12 md:py-0 md:w-[25%] lg:w-[20%] flex flex-col justify-center items-center relative overflow-hidden bg-[#0a0a0a]">

        {/* Animated Connecting Lines / Conversation flow */}
        <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
           {/* Center vertical flow */}
           <div className="absolute top-0 bottom-0 w-px bg-[#262626]" />

           {/* Flow pulses */}
           <div className="absolute h-full w-px overflow-hidden">
             <div className="h-1/3 w-full bg-gradient-to-b from-transparent via-[#fafafa] to-transparent opacity-30 animate-extract-vertical" />
           </div>
        </div>

        <div className="flex flex-col items-center z-20 bg-[#0a0a0a] px-4 py-5 border border-[#262626] rounded-lg shadow-[0_0_20px_rgba(0,0,0,0.8)] w-4/5 text-center transition-all duration-700 ease-out scale-105">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#fafafa] mb-3 animate-pulse opacity-80">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <rect x="7" y="7" width="3" height="9"></rect>
            <rect x="14" y="7" width="3" height="5"></rect>
          </svg>
          <div className="text-[8px] font-bold text-[#fafafa] uppercase tracking-widest text-center flex flex-col items-center gap-1.5">
            SYNTHESIZING
          </div>
        </div>

        {/* Evaluation Indicators */}
        <div className="relative mt-6 md:absolute md:inset-x-0 md:top-[60%] md:mt-4 flex flex-col items-center gap-2 z-10 w-full px-2">
          <div className="w-full px-2 py-1.5 bg-[#111111] border border-[#262626] rounded-full text-[7px] font-bold uppercase tracking-widest text-[#fafafa] shadow-md flex items-center justify-center gap-1.5">
            <span className="w-1 h-1 rounded-full bg-[#fafafa]"></span> Match Verified
          </div>
          <div className="w-full px-2 py-1.5 bg-[#111111] border border-[#262626] rounded-full text-[7px] font-bold uppercase tracking-widest text-[#fafafa] shadow-md flex items-center justify-center gap-1.5">
            <span className="w-1 h-1 rounded-full bg-[#fafafa]"></span> Screening Verified
          </div>
          <div className="w-full px-2 py-1.5 bg-[#111111] border border-[#262626] rounded-full text-[7px] font-bold uppercase tracking-widest text-[#fafafa] shadow-md flex items-center justify-center gap-1.5">
            <span className="w-1 h-1 rounded-full bg-[#fafafa]"></span> Evaluation Verified
          </div>
        </div>

        <div className="absolute bottom-6 text-[9px] font-bold text-[#8c8c8c] uppercase tracking-widest flex items-center gap-1.5">
          <span className="w-1 h-1 rounded-full bg-[#8c8c8c] animate-pulse"></span>
          AI Decision Engine
        </div>

        {/* Subtle background grid/lines */}
        <div className="absolute inset-0 pointer-events-none opacity-[0.05]"
             style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,1) 1px, transparent 1px)', backgroundSize: '100% 24px' }} />
      </div>

      {/* Right: Hiring Recommendation */}
      <div className="w-full md:w-[37.5%] lg:w-[40%] bg-[#0a0a0a] border-t md:border-t-0 md:border-l border-[#262626] p-6 flex flex-col justify-between overflow-hidden relative">
        <div className="flex flex-col h-full relative z-10">
          <div className="flex items-center justify-between mb-5 pb-4 border-b border-[#262626]">
            <div className="text-[11px] font-bold text-[#fafafa] uppercase tracking-widest flex items-center gap-2">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#8c8c8c]">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
              Hiring Recommendation
            </div>
            <div className="text-[9px] font-bold text-[#8c8c8c] uppercase tracking-widest flex items-center gap-1.5">
              FINAL CONFIDENCE
            </div>
          </div>

          <div className="mb-4">
            <div className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-1 flex items-center gap-1.5">
              Confidence Score
            </div>
            <div className="text-4xl font-bold text-[#fafafa] tracking-tighter flex items-end gap-2">
              92<span className="text-xl text-[#8c8c8c] mb-1">%</span>
            </div>
          </div>

          <div className="mb-4">
             <div className="text-[9px] font-bold text-[#8c8c8c] uppercase tracking-widest mb-1.5">Decision Signals</div>
             <ul className="text-[11px] text-[#fafafa] space-y-1.5">
               <li className="flex gap-1.5 items-center"><span className="text-[#a3a3a3] text-[14px] leading-none">✓</span>High technical match</li>
               <li className="flex gap-1.5 items-center"><span className="text-[#a3a3a3] text-[14px] leading-none">✓</span>Strong problem-solving</li>
               <li className="flex gap-1.5 items-center"><span className="text-[#a3a3a3] text-[14px] leading-none">✓</span>Low risk profile</li>
             </ul>
          </div>

          <div className="mt-auto pt-4 border-t border-[#262626]">
            <div className="text-[10px] font-bold uppercase tracking-widest flex items-center justify-between">
              <span className="text-[#fafafa]">Extend Offer</span>
              <span className="text-[#fafafa] flex items-center gap-1">Create offer <span className="text-[14px]">→</span></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function OfferStage(): React.ReactElement {
  return (
    <div className="flex flex-col md:flex-row w-full h-full bg-[#0a0a0a]">
      {/* Left: Offer Summary */}
      <div className="w-full md:w-[37.5%] lg:w-[40%] bg-[#111111] border-b md:border-b-0 md:border-r border-[#262626] p-6 relative overflow-hidden flex flex-col justify-between">
        <div className="flex flex-col relative z-10">
          <div className="text-[11px] font-bold text-[#fafafa] uppercase tracking-widest mb-6 pb-4 border-b border-[#262626] flex items-center gap-2">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#8c8c8c]">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
            Offer Summary
          </div>

          <div className="mb-5 flex justify-between items-start">
            <div>
              <div className="text-xl font-serif text-[#fafafa] tracking-tight mb-0.5">David Kim</div>
              <div className="text-[12px] text-[#a3a3a3] mb-1">Senior Backend Engineer</div>
              <div className="text-[10px] text-[#8c8c8c]">Bengaluru</div>
            </div>
            <div className="px-2 py-1 bg-[#262626] text-[#fafafa] text-[9px] font-bold rounded uppercase tracking-wider border border-[#404040]">
              Ready to send
            </div>
          </div>

          <div>
            <div className="space-y-3 mt-1">
              <div className="flex justify-between items-center border-b border-[#262626] pb-2">
                <span className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest">Base Compensation</span>
                <span className="text-[11px] text-[#fafafa] font-semibold">₹4,200,000 / yr</span>
              </div>
              <div className="flex justify-between items-center border-b border-[#262626] pb-2">
                <span className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest">Start Date</span>
                <span className="text-[11px] text-[#fafafa] font-semibold">Oct 14, 2026</span>
              </div>
              <div className="flex justify-between items-center border-b border-[#262626] pb-2">
                <span className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest">Employment Type</span>
                <span className="text-[11px] text-[#fafafa] font-semibold">Full-time</span>
              </div>
              <div className="flex justify-between items-center pb-1">
                <span className="text-[10px] font-bold text-[#8c8c8c] uppercase tracking-widest">Reporting To</span>
                <span className="text-[11px] text-[#fafafa] font-semibold">VP of Engineering</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Center: AI Offer Engine */}
      <div className="w-full py-12 md:py-0 md:w-[25%] lg:w-[20%] flex flex-col justify-center items-center relative overflow-hidden bg-[#0a0a0a]">

        {/* Animated Connecting Lines / Conversation flow */}
        <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
           {/* Center vertical flow */}
           <div className="absolute top-0 bottom-0 w-px bg-[#262626]" />

           {/* Flow pulses */}
           <div className="absolute h-full w-px overflow-hidden">
             <div className="h-1/3 w-full bg-gradient-to-b from-transparent via-[#fafafa] to-transparent opacity-30 animate-extract-vertical" />
           </div>
        </div>

        <div className="flex flex-col items-center z-20 bg-[#0a0a0a] px-4 py-5 border border-[#262626] rounded-lg shadow-[0_0_20px_rgba(0,0,0,0.8)] w-4/5 text-center">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#fafafa] mb-3 opacity-90">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <path d="M12 18v-6"></path>
            <path d="M9 15l3 3 3-3"></path>
          </svg>
          <div className="text-[8px] font-bold text-[#fafafa] uppercase tracking-widest text-center flex flex-col items-center gap-1.5">
            READY
          </div>
        </div>

        {/* Evaluation Indicators */}
        <div className="relative mt-6 md:absolute md:inset-x-0 md:top-[60%] md:mt-4 flex flex-col items-center gap-2 z-10 w-full px-2">
          <div className="w-full px-2 py-1.5 bg-[#111111] border border-[#262626] rounded-full text-[7px] font-bold uppercase tracking-widest text-[#fafafa] shadow-md flex items-center justify-center gap-1.5">
            <span className="w-1 h-1 rounded-full bg-[#fafafa]"></span> Candidate Verified
          </div>
          <div className="w-full px-2 py-1.5 bg-[#111111] border border-[#262626] rounded-full text-[7px] font-bold uppercase tracking-widest text-[#fafafa] shadow-md flex items-center justify-center gap-1.5">
            <span className="w-1 h-1 rounded-full bg-[#fafafa]"></span> Role Verified
          </div>
          <div className="w-full px-2 py-1.5 bg-[#111111] border border-[#262626] rounded-full text-[7px] font-bold uppercase tracking-widest text-[#fafafa] shadow-md flex items-center justify-center gap-1.5">
            <span className="w-1 h-1 rounded-full bg-[#fafafa]"></span> Terms Verified
          </div>
        </div>

        <div className="absolute bottom-6 text-[9px] font-bold text-[#8c8c8c] uppercase tracking-widest flex items-center gap-1.5">
          <span className="w-1 h-1 rounded-full bg-[#8c8c8c]"></span>
          Offer Generation
        </div>

        {/* Subtle background grid/lines */}
        <div className="absolute inset-0 pointer-events-none opacity-[0.05]"
             style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,1) 1px, transparent 1px)', backgroundSize: '100% 24px' }} />
      </div>

      {/* Right: Offer Ready */}
      <div className="w-full md:w-[37.5%] lg:w-[40%] bg-[#0a0a0a] border-t md:border-t-0 md:border-l border-[#262626] p-6 flex flex-col justify-between overflow-hidden relative">
        <div className="flex flex-col h-full relative z-10">
          <div className="flex items-center justify-between mb-5 pb-4 border-b border-[#262626]">
            <div className="text-[11px] font-bold text-[#fafafa] uppercase tracking-widest flex items-center gap-2">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#8c8c8c]">
                <polyline points="9 11 12 14 22 4"></polyline>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
              </svg>
              Offer Ready
            </div>
            <div className="text-[9px] font-bold text-[#8c8c8c] uppercase tracking-widest flex items-center gap-1.5">
              READY TO SEND
            </div>
          </div>

          <div className="mb-5">
            <div className="text-[16px] font-bold text-[#fafafa] tracking-tight mb-1">
              David Kim
            </div>
            <div className="text-[11px] text-[#a3a3a3]">
              Senior Backend Engineer
            </div>
          </div>

          <div className="mb-5">
             <p className="text-[12px] text-[#fafafa] leading-relaxed font-serif italic opacity-90 border-l-2 border-[#404040] pl-3">
               &quot;Offer terms align with the approved role, candidate evaluation, and hiring decision.&quot;
             </p>
          </div>

          <div className="mb-4">
             <ul className="text-[10px] text-[#a3a3a3] space-y-2 uppercase tracking-widest font-bold">
               <li className="flex gap-2 items-center"><span className="text-[#fafafa] text-[12px] leading-none">✓</span>Hiring decision approved</li>
               <li className="flex gap-2 items-center"><span className="text-[#fafafa] text-[12px] leading-none">✓</span>Compensation defined</li>
               <li className="flex gap-2 items-center"><span className="text-[#fafafa] text-[12px] leading-none">✓</span>Offer terms verified</li>
             </ul>
          </div>

          <div className="mt-auto pt-4 border-t border-[#262626]">
            <div className="text-[10px] font-bold uppercase tracking-widest flex items-center justify-between">
              <span className="text-[#8c8c8c]">Offer Verified</span>
              <span className="text-[#fafafa] flex items-center gap-1">Send offer <span className="text-[14px]">→</span></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
