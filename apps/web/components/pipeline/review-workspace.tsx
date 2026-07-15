"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { SignOutButton } from "@/components/auth-buttons"
import { api } from "@/lib/api/client"
import { endpoints } from "@/lib/api/endpoints"
import type { DiffLine, PullRequest, PullRequestDetail } from "@/lib/api/types"
import { parseUnifiedDiff } from "@/lib/utils/diff-parser"

type StageId = "validation" | "retrieval" | "generation"
type StageStatus = "pending" | "running" | "done" | "error"

type Stage = {
  id: StageId
  label: string
  detail: string
  status: StageStatus
}

const INITIAL_STAGES: Stage[] = [
  { id: "validation", label: "Validation", detail: "", status: "pending" },
  { id: "retrieval", label: "Retrieval", detail: "", status: "pending" },
  { id: "generation", label: "Generation", detail: "", status: "pending" },
]

function lineClass(type: DiffLine["type"]) {
  if (type === "add") return "bg-emerald-400/[0.07] text-emerald-100"
  if (type === "del") return "bg-rose-400/[0.08] text-rose-100"
  if (type === "meta" || type === "ctx") return "text-[#8bd8c7]/80"
  return "text-white/65"
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
      <div className="flex h-11 shrink-0 items-center border-b border-white/10 bg-white/[0.025] px-4">
        <p className="truncate font-[family-name:var(--font-mono)] text-[12px] text-white/45">{meta}</p>
      </div>
      <div className="min-h-0 flex-1 overflow-auto bg-[#080a0d]">
        {lines.length === 0 ? (
          <p className="p-4 text-sm text-white/35">No diff to display.</p>
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

function patchStage(
  stages: Stage[],
  id: StageId,
  patch: Partial<Pick<Stage, "status" | "detail">>,
): Stage[] {
  return stages.map((s) => (s.id === id ? { ...s, ...patch } : s))
}

export function ReviewWorkspace({
  owner,
  repo,
}: {
  owner: string
  repo: string
}) {
  const [pulls, setPulls] = useState<PullRequest[]>([])
  const [selectedNumber, setSelectedNumber] = useState<number | null>(null)
  const [detail, setDetail] = useState<PullRequestDetail | null>(null)
  const [stages, setStages] = useState<Stage[]>(INITIAL_STAGES)
  const [error, setError] = useState<string | null>(null)

  const diffLines = useMemo(
    () => (detail ? parseUnifiedDiff(detail.diff) : []),
    [detail],
  )

  // Stage 1: validate access + list open PRs
  useEffect(() => {
    let cancelled = false

    async function validate() {
      setError(null)
      setDetail(null)
      setPulls([])
      setSelectedNumber(null)
      setStages(
        INITIAL_STAGES.map((s) =>
          s.id === "validation"
            ? { ...s, status: "running", detail: "Checking repository access" }
            : { ...s, status: "pending", detail: "" },
        ),
      )

      try {
        const list = await api.get<PullRequest[]>(endpoints.prs.list(owner, repo))
        if (cancelled) return

        setPulls(list)
        setStages((prev) =>
          patchStage(prev, "validation", {
            status: "done",
            detail: list.length
              ? `${list.length} open pull request${list.length === 1 ? "" : "s"}`
              : "No open pull requests",
          }),
        )

        if (list.length === 0) {
          setStages((prev) =>
            prev.map((s) =>
              s.id === "validation"
                ? s
                : { ...s, status: "done", detail: "Skipped" },
            ),
          )
          return
        }

        setSelectedNumber(list[0]!.number)
      } catch (err) {
        if (cancelled) return
        const message = err instanceof Error ? err.message : "Validation failed"
        setError(message)
        setStages((prev) =>
          patchStage(prev, "validation", { status: "error", detail: message }),
        )
      }
    }

    void validate()
    return () => {
      cancelled = true
    }
  }, [owner, repo])

  // Stages 2-3: fetch diff for the selected PR, then surface files
  useEffect(() => {
    if (selectedNumber === null) return

    let cancelled = false

    async function retrieveAndGenerate() {
      setDetail(null)
      setError(null)
      setStages((prev) =>
        prev
          .map((s) =>
            s.id === "retrieval"
              ? { ...s, status: "running" as const, detail: "Loading pull request diff" }
              : s.id === "generation"
                ? { ...s, status: "pending" as const, detail: "" }
                : s,
          ),
      )

      try {
        const pr = await api.get<PullRequestDetail>(
          endpoints.prs.detail(owner, repo, selectedNumber!),
        )
        if (cancelled) return

        setDetail(pr)
        setStages((prev) =>
          prev.map((s) => {
            if (s.id === "retrieval") {
              return {
                ...s,
                status: "done" as const,
                detail: `${pr.changed_files || pr.files.length} files · +${pr.additions} / -${pr.deletions}`,
              }
            }
            if (s.id === "generation") {
              return {
                ...s,
                status: "running" as const,
                detail: "Parsing diff surface",
              }
            }
            return s
          }),
        )

        await new Promise<void>((resolve) => {
          requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
        })
        if (cancelled) return

        const lineCount = parseUnifiedDiff(pr.diff).length
        setStages((prev) =>
          patchStage(prev, "generation", {
            status: "done",
            detail: `${lineCount} diff line${lineCount === 1 ? "" : "s"} ready`,
          }),
        )
      } catch (err) {
        if (cancelled) return
        const message = err instanceof Error ? err.message : "Retrieval failed"
        setError(message)
        setStages((prev) =>
          patchStage(prev, "retrieval", { status: "error", detail: message }),
        )
      }
    }

    void retrieveAndGenerate()
    return () => {
      cancelled = true
    }
  }, [owner, repo, selectedNumber])

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
        <SignOutButton />
      </header>

      {error ? (
        <div className="shrink-0 border-b border-rose-400/20 bg-rose-400/10 px-4 py-2 text-sm text-rose-100">
          {error}
        </div>
      ) : null}

      <section className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[minmax(0,1fr)_280px]">
        <DiffPanel
          lines={diffLines}
          meta={
            detail
              ? `#${detail.number} ${detail.title}`
              : pulls.length === 0 && stages[0]?.status === "done"
                ? "No open pull requests"
                : "Waiting for pull request"
          }
        />

        <aside className="flex min-h-0 flex-col bg-[#0c0e12]">
          <div className="shrink-0 border-b border-white/10 px-5 py-4">
            <p className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.16em] text-white/35">
              Pipeline
            </p>
            <DotPipeline stages={stages} />
          </div>

          <div className="min-h-0 flex-1 overflow-auto px-5 py-4">
            {pulls.length > 0 ? (
              <>
                <p className="mb-3 font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.16em] text-white/35">
                  Open PRs
                </p>
                <div className="space-y-1">
                  {pulls.map((pr) => {
                    const active = pr.number === selectedNumber
                    return (
                      <button
                        key={pr.number}
                        type="button"
                        onClick={() => setSelectedNumber(pr.number)}
                        className={`w-full rounded-md px-3 py-2.5 text-left transition active:translate-y-px ${
                          active
                            ? "bg-[var(--accent)]/10 text-white"
                            : "text-white/55 hover:bg-white/[0.04] hover:text-white/80"
                        }`}
                      >
                        <p className="truncate text-[13px] font-medium">
                          <span className="font-[family-name:var(--font-mono)] text-white/35">
                            #{pr.number}
                          </span>{" "}
                          {pr.title}
                        </p>
                        <p className="mt-1 font-[family-name:var(--font-mono)] text-[11px] text-white/30">
                          {pr.head_branch} → {pr.base_branch}
                        </p>
                      </button>
                    )
                  })}
                </div>
              </>
            ) : null}

            {detail ? (
              <div className="mt-6">
                <p className="mb-3 font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.16em] text-white/35">
                  Changed files
                </p>
                <ul className="space-y-2">
                  {detail.files.map((file) => (
                    <li key={file.filename} className="min-w-0">
                      <p className="truncate font-[family-name:var(--font-mono)] text-[12px] text-white/70">
                        {file.filename}
                      </p>
                      <p className="mt-0.5 font-[family-name:var(--font-mono)] text-[11px] text-white/30">
                        {file.status} · +{file.additions} / -{file.deletions}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </aside>
      </section>
    </main>
  )
}
