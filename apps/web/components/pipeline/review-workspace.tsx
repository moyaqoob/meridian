"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import { SignOutButton } from "@/components/auth-buttons"
import { api, APIError } from "@/lib/api/client"
import { endpoints } from "@/lib/api/endpoints"
import type {
  DiffLine,
  PullRequest,
  PullRequestDetail,
  ReviewFinding,
  ReviewJob,
  ReviewOut,
  StageUpdateEvent,
} from "@/lib/api/types"
import { parseUnifiedDiff } from "@/lib/utils/diff-parser"

type StageId = "validation" | "retrieval" | "generation"
type StageStatus = "pending" | "running" | "done" | "error"
type WorkspaceMode = "inbox" | "reviewing" | "complete"

type Stage = {
  id: StageId
  label: string
  detail: string
  status: StageStatus
}

const IDLE_STAGES: Stage[] = [
  { id: "validation", label: "Validation", detail: "Waiting for approval", status: "pending" },
  { id: "retrieval", label: "Retrieval", detail: "Waiting", status: "pending" },
  { id: "generation", label: "Generation", detail: "Waiting", status: "pending" },
]

function lineClass(type: DiffLine["type"]) {
  if (type === "add") return "bg-emerald-400/[0.07] text-emerald-100"
  if (type === "del") return "bg-rose-400/[0.08] text-rose-100"
  if (type === "meta" || type === "ctx") return "text-[#8bd8c7]/80"
  return "text-white/65"
}

function severityClass(severity: ReviewFinding["severity"]) {
  if (severity === "high") return "bg-rose-400/14 text-rose-200 ring-rose-300/25"
  if (severity === "medium") return "bg-amber-400/14 text-amber-200 ring-amber-300/25"
  return "bg-emerald-400/12 text-emerald-200 ring-emerald-300/25"
}

function PanelHeader({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-white/10 bg-white/[0.025] px-4">
      <div className="min-w-0">
        <h2 className="text-sm font-semibold text-white">{title}</h2>
        <p className="truncate font-[family-name:var(--font-mono)] text-[11px] text-white/40">
          {detail}
        </p>
      </div>
    </div>
  )
}

function DotPipeline({ stages }: { stages: Stage[] }) {
  return (
    <ol className="relative flex flex-col py-2">
      {stages.map((stage, index) => (
        <li key={stage.id} className="relative flex gap-4 pb-8 last:pb-0">
          {index < stages.length - 1 ? (
            <span
              aria-hidden
              className={`absolute left-[7px] top-4 w-px ${
                stage.status === "done"
                  ? "bg-[var(--accent)]/70"
                  : stage.status === "running"
                    ? "bg-[var(--accent)]/35"
                    : "bg-white/10"
              }`}
              style={{ height: "calc(100% - 8px)" }}
            />
          ) : null}

          <span className="relative z-[1] mt-1 flex size-4 shrink-0 items-center justify-center">
            <span
              className={`size-2.5 rounded-full transition-colors duration-300 ${
                stage.status === "done"
                  ? "bg-[var(--accent)] shadow-[0_0_12px_rgba(125,245,212,0.35)]"
                  : stage.status === "running"
                    ? "animate-pulse bg-[var(--accent)]/80"
                    : stage.status === "error"
                      ? "bg-rose-400"
                      : "bg-white/20 ring-1 ring-white/15"
              }`}
            />
          </span>

          <div className="min-w-0 flex-1 pt-0.5">
            <p
              className={`font-[family-name:var(--font-mono)] text-[12px] uppercase tracking-[0.14em] ${
                stage.status === "pending" ? "text-white/30" : "text-white/80"
              }`}
            >
              {stage.label}
            </p>
            <p
              className={`mt-1 text-[12px] leading-5 ${
                stage.status === "error"
                  ? "text-rose-300"
                  : stage.status === "pending"
                    ? "text-white/25"
                    : "text-white/45"
              }`}
            >
              {stage.detail || "Waiting"}
            </p>
          </div>
        </li>
      ))}
    </ol>
  )
}

function DiffPanel({ lines, meta }: { lines: DiffLine[]; meta: string }) {
  return (
    <section className="flex min-h-0 min-w-0 flex-col border-b border-white/10 lg:border-b-0 lg:border-r">
      <PanelHeader title="Diff" detail={meta} />
      <div className="min-h-0 flex-1 overflow-auto bg-[#080a0d]">
        {lines.length === 0 ? (
          <div className="flex h-full items-center justify-center p-6">
            <p className="max-w-sm text-center text-sm leading-6 text-white/35">
              Approve a pull request to load its diff.
            </p>
          </div>
        ) : (
          <div className="inline-block min-w-full py-2 font-[family-name:var(--font-mono)] text-[12px] leading-6">
            {lines.map((line, index) => (
              <div
                key={`${index}-${line.type}-${line.text.slice(0, 32)}`}
                className={`flex ${lineClass(line.type)}`}
              >
                <span className="w-10 shrink-0 select-none pr-2 text-right text-white/20">
                  {line.newLine ?? line.oldLine ?? ""}
                </span>
                <span className="whitespace-pre pr-4">{line.text || " "}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

function ReviewPanel({
  review,
  isRunning,
}: {
  review: ReviewOut | null
  isRunning: boolean
}) {
  return (
    <section className="flex min-h-0 min-w-0 flex-col border-t border-white/10 lg:border-l lg:border-t-0">
      <PanelHeader
        title="Review"
        detail={
          review
            ? `${review.findings.length} finding${review.findings.length === 1 ? "" : "s"}`
            : isRunning
              ? "Generating…"
              : "Awaiting approval"
        }
      />
      <div className="min-h-0 flex-1 overflow-auto p-4">
        {!review && !isRunning ? (
          <p className="text-sm leading-6 text-white/35">
            Findings appear here after a review runs — via webhook or Approve.
          </p>
        ) : null}

        {isRunning && !review ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="rounded-md border border-white/10 bg-white/[0.03] p-4">
                <div className="h-3 w-16 animate-pulse rounded bg-white/[0.08]" />
                <div className="mt-3 h-4 w-3/4 animate-pulse rounded bg-white/[0.06]" />
                <div className="mt-2 h-3 w-full animate-pulse rounded bg-white/[0.04]" />
              </div>
            ))}
          </div>
        ) : null}

        {review ? (
          <div className="space-y-4">
            <div className="rounded-md border border-white/10 bg-white/[0.03] p-4">
              <p className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.14em] text-white/35">
                Summary
              </p>
              <p className="mt-2 text-sm leading-6 text-white/75">{review.summary}</p>
            </div>

            <div className="space-y-3">
              {review.findings.map((finding) => (
                <article
                  key={finding.id}
                  className="rounded-md border border-white/10 bg-white/[0.03] p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <span
                      className={`rounded-full px-2 py-1 text-[11px] uppercase tracking-wide ring-1 ${severityClass(finding.severity)}`}
                    >
                      {finding.severity}
                    </span>
                    <span className="truncate font-[family-name:var(--font-mono)] text-[11px] text-white/35">
                      {finding.file_path || finding.category}
                    </span>
                  </div>
                  <h3 className="mt-3 text-sm font-semibold leading-5 text-white">
                    {finding.title}
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-white/55">{finding.comment}</p>
                </article>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  )
}

function mapStageUpdate(prev: Stage[], event: StageUpdateEvent): Stage[] {
  const stageMap: Record<string, StageId> = {
    validation: "validation",
    retrieval: "retrieval",
    generation: "generation",
    "citation-mapping": "generation",
    complete: "generation",
  }
  const target = stageMap[event.stage]
  if (!target) return prev

  const order: StageId[] = ["validation", "retrieval", "generation"]
  const targetIdx = order.indexOf(target)

  return prev.map((s) => {
    const idx = order.indexOf(s.id)
    if (event.stage === "complete") {
      return { ...s, status: "done", detail: s.id === "generation" ? event.message : s.detail }
    }
    if (idx < targetIdx) return { ...s, status: "done" }
    if (s.id === target) {
      return {
        ...s,
        status: "running",
        detail: event.message,
      }
    }
    return s
  })
}

async function waitForReviewId(
  owner: string,
  repo: string,
  number: number,
  headSha: string,
): Promise<ReviewJob> {
  const started = Date.now()
  while (Date.now() - started < 60_000) {
    try {
      const job = await api.get<ReviewJob>(
        endpoints.prs.reviewStatus(owner, repo, number, headSha),
      )
      if (job.review_id) return job
    } catch (err) {
      if (!(err instanceof APIError && err.status === 404)) throw err
    }
    await new Promise((r) => setTimeout(r, 500))
  }
  throw new Error("Timed out waiting for review job to start")
}

export function ReviewWorkspace({
  owner,
  repo,
}: {
  owner: string
  repo: string
}) {
  const [pulls, setPulls] = useState<PullRequest[]>([])
  const [pendingNumber, setPendingNumber] = useState<number | null>(null)
  const [detail, setDetail] = useState<PullRequestDetail | null>(null)
  const [review, setReview] = useState<ReviewOut | null>(null)
  const [stages, setStages] = useState<Stage[]>(IDLE_STAGES)
  const [mode, setMode] = useState<WorkspaceMode>("inbox")
  const [error, setError] = useState<string | null>(null)
  const [loadingPulls, setLoadingPulls] = useState(true)
  const [repoId, setRepoId] = useState<string | null>(null)
  const streamRef = useRef<EventSource | null>(null)

  const diffLines = useMemo(
    () => (detail ? parseUnifiedDiff(detail.diff) : []),
    [detail],
  )

  const pendingPr = useMemo(
    () => pulls.find((p) => p.number === pendingNumber) ?? null,
    [pulls, pendingNumber],
  )

  function closeStream() {
    streamRef.current?.close()
    streamRef.current = null
  }

  function applyComplete(payload: {
    review_id: string
    summary: string
    findings: ReviewFinding[]
    timings?: Record<string, number>
  }) {
    setReview({
      review_id: payload.review_id,
      pr_id: "",
      summary: payload.summary,
      pr_type: "chore",
      findings: payload.findings,
      model_version: "",
      timings: payload.timings ?? {},
    })
    setStages((prev) =>
      prev.map((s) => ({
        ...s,
        status: "done" as const,
        detail:
          s.id === "generation"
            ? `${payload.findings.length} findings`
            : s.detail || "Done",
      })),
    )
    setMode("complete")
  }

  function subscribeToReview(reviewId: string) {
    closeStream()
    setMode("reviewing")
    setError(null)

    const es = new EventSource(endpoints.review.stream(reviewId), {
      withCredentials: true,
    })
    streamRef.current = es

    es.addEventListener("stage-update", (evt) => {
      try {
        const data = JSON.parse(evt.data) as StageUpdateEvent
        setStages((prev) => mapStageUpdate(prev, data))
      } catch {
        // ignore malformed
      }
    })

    es.addEventListener("generation-chunk", () => {
      setStages((prev) =>
        prev.map((s) =>
          s.id === "generation"
            ? { ...s, status: "running", detail: "Streaming model output…" }
            : s.id === "retrieval" || s.id === "validation"
              ? { ...s, status: "done" }
              : s,
        ),
      )
    })

    es.addEventListener("complete", (evt) => {
      try {
        const data = JSON.parse(evt.data) as {
          review_id: string
          summary: string
          findings: ReviewFinding[]
          timings?: Record<string, number>
        }
        applyComplete(data)
      } catch {
        setError("Failed to parse complete event")
      }
      closeStream()
    })

    es.addEventListener("error", (evt) => {
      // EventSource also fires "error" on connection drop; only handle named SSE errors.
      if (evt instanceof MessageEvent && evt.data) {
        try {
          const data = JSON.parse(evt.data) as {
            stage?: string
            message?: string
          }
          const message = data.message || "Review failed"
          setError(message)
          setStages((prev) => {
            const active = prev.find((s) => s.status === "running")?.id ?? "generation"
            return prev.map((s) =>
              s.id === active ? { ...s, status: "error", detail: message } : s,
            )
          })
          setMode("inbox")
        } catch {
          // connection-level error; EventSource will retry — replay covers gaps
        }
      }
    })
  }

  useEffect(() => {
    return () => closeStream()
  }, [])

  useEffect(() => {
    let cancelled = false

    async function ensureReady() {
      try {
        const available = await api.get<
          Array<{
            full_name: string
            ingest_status: string | null
            connected: boolean
            repo_id: string | null
          }>
        >(endpoints.repos.available())
        if (cancelled) return
        const fullName = `${owner}/${repo}`
        const hit = available.find((r) => r.full_name === fullName)
        if (!hit || !hit.connected || hit.ingest_status !== "ready") {
          window.location.replace("/dashboard")
          return
        }
        setRepoId(hit.repo_id)
      } catch {
        // Dashboard remains reachable if this check fails.
      }
    }

    void ensureReady()
    return () => {
      cancelled = true
    }
  }, [owner, repo])

  useEffect(() => {
    let cancelled = false

    async function loadPulls() {
      setLoadingPulls(true)
      setError(null)
      try {
        const list = await api.get<PullRequest[]>(endpoints.prs.list(owner, repo))
        if (cancelled) return
        setPulls(list)
        setPendingNumber(list[0]?.number ?? null)

        // Auto-attach to an existing/in-flight review (webhook path).
        for (const pr of list) {
          try {
            const job = await api.get<ReviewJob>(
              endpoints.prs.reviewStatus(owner, repo, pr.number),
            )
            if (cancelled || !job.review_id) continue

            setPendingNumber(pr.number)
            const prDetail = await api.get<PullRequestDetail>(
              endpoints.prs.detail(owner, repo, pr.number),
            )
            if (cancelled) return
            setDetail(prDetail)

            if (job.status === "complete" && job.review) {
              setReview(job.review)
              setStages([
                { id: "validation", label: "Validation", detail: "Done", status: "done" },
                { id: "retrieval", label: "Retrieval", detail: "Done", status: "done" },
                {
                  id: "generation",
                  label: "Generation",
                  detail: `${job.review.findings.length} findings`,
                  status: "done",
                },
              ])
              setMode("complete")
              break
            }

            if (job.status === "error") {
              setPendingNumber(pr.number)
              setError(job.message || "Review failed")
              setStages((prev) =>
                prev.map((s) =>
                  s.status === "running" || s.status === "error"
                    ? { ...s, status: "error", detail: job.message || "Failed" }
                    : s,
                ),
              )
              break
            }

            if (job.status === "running" || job.status === "queued" || job.status === "exists") {
              setStages([
                {
                  id: "validation",
                  label: "Validation",
                  detail: "Resuming…",
                  status: "running",
                },
                { id: "retrieval", label: "Retrieval", detail: "Waiting", status: "pending" },
                { id: "generation", label: "Generation", detail: "Waiting", status: "pending" },
              ])
              subscribeToReview(job.review_id)
              break
            }
          } catch {
            // No review yet for this PR.
          }
        }
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : "Failed to load pull requests")
      } finally {
        if (!cancelled) setLoadingPulls(false)
      }
    }

    void loadPulls()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- attach once per repo
  }, [owner, repo])

  useEffect(() => {
    if (mode !== "inbox" || !pendingNumber) return

    let cancelled = false
    const timer = window.setInterval(() => {
      void (async () => {
        try {
          const job = await api.get<ReviewJob>(
            endpoints.prs.reviewStatus(owner, repo, pendingNumber),
          )
          if (cancelled || !job.review_id) return

          const prDetail = await api.get<PullRequestDetail>(
            endpoints.prs.detail(owner, repo, pendingNumber),
          )
          if (cancelled) return
          setDetail(prDetail)

          if (job.status === "complete" && job.review) {
            setReview(job.review)
            setStages([
              { id: "validation", label: "Validation", detail: "Done", status: "done" },
              { id: "retrieval", label: "Retrieval", detail: "Done", status: "done" },
              {
                id: "generation",
                label: "Generation",
                detail: `${job.review.findings.length} findings`,
                status: "done",
              },
            ])
            setMode("complete")
            return
          }

          if (job.status === "error") {
            setError(job.message || "Review failed")
            return
          }

          if (job.status === "running" || job.status === "queued" || job.status === "exists") {
            setStages([
              {
                id: "validation",
                label: "Validation",
                detail: "Resuming…",
                status: "running",
              },
              { id: "retrieval", label: "Retrieval", detail: "Waiting", status: "pending" },
              { id: "generation", label: "Generation", detail: "Waiting", status: "pending" },
            ])
            subscribeToReview(job.review_id)
          }
        } catch {
          // No review yet.
        }
      })()
    }, 2500)

    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, pendingNumber, owner, repo])

  async function approveAndRun(prNumber: number) {
    setMode("reviewing")
    setError(null)
    setDetail(null)
    setReview(null)
    setStages([
      { id: "validation", label: "Validation", detail: "Loading pull request", status: "running" },
      { id: "retrieval", label: "Retrieval", detail: "Waiting", status: "pending" },
      { id: "generation", label: "Generation", detail: "Waiting", status: "pending" },
    ])

    try {
      const pr = await api.get<PullRequestDetail>(
        endpoints.prs.detail(owner, repo, prNumber),
      )
      setDetail(pr)

      const job = await api.post<ReviewJob>(endpoints.prs.review(owner, repo, prNumber))

      if (job.status === "complete" && job.review) {
        setReview(job.review)
        setStages([
          { id: "validation", label: "Validation", detail: "Done", status: "done" },
          { id: "retrieval", label: "Retrieval", detail: "Done", status: "done" },
          {
            id: "generation",
            label: "Generation",
            detail: `${job.review.findings.length} findings`,
            status: "done",
          },
        ])
        setMode("complete")
        return
      }

      let reviewId = job.review_id
      if (!reviewId) {
        const started = await waitForReviewId(owner, repo, prNumber, job.head_sha)
        reviewId = started.review_id
        if (started.status === "complete" && started.review) {
          setReview(started.review)
          setMode("complete")
          setStages((prev) => prev.map((s) => ({ ...s, status: "done" })))
          return
        }
      }
      if (!reviewId) throw new Error("Review job did not return an id")

      setStages([
        {
          id: "validation",
          label: "Validation",
          detail: `#${pr.number} queued`,
          status: "done",
        },
        {
          id: "retrieval",
          label: "Retrieval",
          detail: "Waiting for worker…",
          status: "running",
        },
        { id: "generation", label: "Generation", detail: "Waiting", status: "pending" },
      ])
      subscribeToReview(reviewId)
    } catch (err) {
      const message = err instanceof Error ? err.message : "Review pipeline failed"
      setError(message)
      setStages((prev) => {
        const active = prev.find((s) => s.status === "running")?.id ?? "validation"
        return prev.map((s) =>
          s.id === active ? { ...s, status: "error", detail: message } : s,
        )
      })
      setMode("inbox")
    }
  }

  function dismissNotification() {
    if (!pendingNumber) return
    const rest = pulls.filter((p) => p.number !== pendingNumber)
    setPulls(rest)
    setPendingNumber(rest[0]?.number ?? null)
  }

  const high = review?.findings.filter((f) => f.severity === "high").length ?? 0
  const medium = review?.findings.filter((f) => f.severity === "medium").length ?? 0
  const low = review?.findings.filter((f) => f.severity === "low").length ?? 0

  return (
    <main className="flex h-dvh flex-col overflow-hidden bg-[#07080b] text-[#f3f5f0]">
      <header className="flex shrink-0 items-center justify-between gap-4 border-b border-white/10 bg-[#090a0d] px-4 py-3 md:px-5">
        <div className="min-w-0">
          <Link
            href="/dashboard"
            className="font-[family-name:var(--font-mono)] text-[11px] text-white/35 no-underline transition hover:text-white/60"
          >
            All repositories
          </Link>
          <h1 className="mt-0.5 truncate font-[family-name:var(--font-mono)] text-base font-semibold tracking-[-0.02em] text-white md:text-lg">
            <span className="text-white/40">{owner}/</span>
            {repo}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          {repoId ? (
            <Link
              href={`/repo/${owner}/${repo}/graph`}
              className="rounded-md border border-white/10 px-3 py-1.5 font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.14em] text-white/55 no-underline transition hover:border-white/25 hover:text-white"
            >
              View Structure
            </Link>
          ) : null}
          <SignOutButton />
        </div>
      </header>

      {error ? (
        <div className="shrink-0 border-b border-rose-400/20 bg-rose-400/10 px-4 py-2 text-sm text-rose-100">
          {error}
        </div>
      ) : null}

      {mode === "inbox" && pendingPr ? (
        <div className="shrink-0 border-b border-[rgba(125,245,212,0.18)] bg-[rgba(125,245,212,0.06)] px-4 py-4 md:px-5">
          <div className="mx-auto flex max-w-[1600px] flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="min-w-0">
              <p className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.16em] text-[var(--accent)]">
                Pull request notification
              </p>
              <p className="mt-1 truncate text-base font-semibold text-white">
                <span className="font-[family-name:var(--font-mono)] text-white/40">
                  #{pendingPr.number}
                </span>{" "}
                {pendingPr.title}
              </p>
              <p className="mt-1 font-[family-name:var(--font-mono)] text-[12px] text-white/40">
                {pendingPr.author} · {pendingPr.head_branch} → {pendingPr.base_branch}
                {pulls.length > 1 ? ` · ${pulls.length} open PRs` : ""}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <button
                type="button"
                onClick={dismissNotification}
                className="rounded-md border border-white/10 px-4 py-2 text-sm text-white/55 transition hover:border-white/25 hover:text-white"
              >
                Dismiss
              </button>
              <button
                type="button"
                onClick={() => void approveAndRun(pendingPr.number)}
                className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-[#06100e] transition hover:bg-[var(--accent-strong)] active:translate-y-px"
              >
                Approve review
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {mode === "inbox" && !loadingPulls && pulls.length === 0 ? (
        <div className="shrink-0 border-b border-white/10 px-4 py-4 text-sm text-white/40 md:px-5">
          No open pull requests for this repository.
        </div>
      ) : null}

      <section className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[minmax(0,1.2fr)_260px_minmax(0,1fr)]">
        <DiffPanel
          lines={diffLines}
          meta={
            detail
              ? `#${detail.number} ${detail.title}`
              : loadingPulls
                ? "Loading pull requests…"
                : "No active review"
          }
        />

        <section className="flex min-h-0 flex-col border-b border-white/10 bg-[#101217] lg:border-b-0 lg:border-r">
          <PanelHeader title="Pipeline" detail="Validation · Retrieval · Generation" />
          <div className="min-h-0 flex-1 overflow-auto px-5 py-4">
            <DotPipeline stages={stages} />

            {pulls.length > 1 && mode === "inbox" ? (
              <div className="mt-6 border-t border-white/10 pt-4">
                <p className="mb-3 font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.16em] text-white/35">
                  Queue
                </p>
                <div className="space-y-1">
                  {pulls.map((pr) => (
                    <button
                      key={pr.number}
                      type="button"
                      onClick={() => setPendingNumber(pr.number)}
                      className={`w-full rounded-md px-3 py-2 text-left text-[13px] transition ${
                        pr.number === pendingNumber
                          ? "bg-[var(--accent)]/10 text-white"
                          : "text-white/50 hover:bg-white/[0.04] hover:text-white/80"
                      }`}
                    >
                      <span className="font-[family-name:var(--font-mono)] text-white/35">
                        #{pr.number}
                      </span>{" "}
                      <span className="truncate">{pr.title}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </section>

        <ReviewPanel review={review} isRunning={mode === "reviewing"} />
      </section>

      <footer className="flex shrink-0 items-center justify-between gap-4 border-t border-white/10 bg-[#090a0d] px-4 py-3 md:px-5">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-white">Summary</p>
          <p className="truncate font-[family-name:var(--font-mono)] text-[11px] text-white/40">
            {detail
              ? `#${detail.number} · +${detail.additions} / -${detail.deletions}`
              : `${owner}/${repo}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {[
            ["High", high],
            ["Medium", medium],
            ["Low", low],
          ].map(([label, count]) => (
            <div
              key={String(label)}
              className="rounded-md border border-white/10 bg-white/[0.035] px-3 py-1.5"
            >
              <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.12em] text-white/35">
                {label}
              </p>
              <p className="text-sm font-semibold text-white">{count}</p>
            </div>
          ))}
        </div>
      </footer>
    </main>
  )
}
