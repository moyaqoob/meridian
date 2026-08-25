"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { SignOutButton } from "@/components/auth-buttons"
import { api } from "@/lib/api/client"
import { endpoints } from "@/lib/api/endpoints"
import type { GitHubRepo, IngestStatus, IngestionStatus, Repo } from "@/lib/api/types"
import type { User } from "@/lib/auth/session"

function statusLabel(status: IngestStatus | null | undefined, connected: boolean) {
  if (!connected || !status) return "Not indexed"
  if (status === "ready") return "Ready"
  if (status === "processing") return "Indexing"
  if (status === "failed") return "Failed"
  return "Pending"
}

function statusClass(status: IngestStatus | null | undefined, connected: boolean) {
  if (!connected || !status) return "border-white/12 bg-white/[0.04] text-white/45"
  if (status === "ready") return "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"
  if (status === "processing") return "border-amber-400/30 bg-amber-400/10 text-amber-200"
  if (status === "failed") return "border-rose-400/30 bg-rose-400/10 text-rose-200"
  return "border-white/12 bg-white/[0.04] text-white/45"
}

function RepoRow({
  repo,
  busyId,
  onIngest,
  onOpen,
}: {
  repo: GitHubRepo
  busyId: string | null
  onIngest: (repo: GitHubRepo) => void
  onOpen: (repo: GitHubRepo) => void
}) {
  const [owner, name] = repo.full_name.split("/")
  const ready = repo.connected && repo.ingest_status === "ready"
  const indexing = repo.ingest_status === "processing"
  const failed = repo.ingest_status === "failed"
  const isBusy = Boolean(busyId && (busyId === repo.repo_id || busyId === repo.full_name))

  return (
    <div className="flex w-full items-center justify-between gap-4 border-b border-white/[0.06] px-1 py-3.5">
      <div className="min-w-0">
        <p className="truncate font-[family-name:var(--font-mono)] text-[13px] text-white/90">
          <span className="text-white/40">{owner}/</span>
          {name}
        </p>
        <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[12px] text-white/35">
          <span>{repo.private ? "Private" : "Public"}</span>
          <span>{repo.default_branch}</span>
          <span
            className={`rounded-full border px-2 py-0.5 text-[11px] ${statusClass(repo.ingest_status, repo.connected)}`}
          >
            {statusLabel(repo.ingest_status, repo.connected)}
            {repo.ingest_status === "ready" && repo.files_ingested
              ? ` · ${repo.files_ingested} files`
              : ""}
          </span>
          {failed && repo.ingest_error ? (
            <span className="max-w-md truncate text-[11px] text-rose-300/80" title={repo.ingest_error}>
              {repo.ingest_error}
            </span>
          ) : null}
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        {!ready ? (
          <button
            type="button"
            disabled={isBusy}
            onClick={() => onIngest(repo)}
            className="rounded-md border border-[var(--accent-dim)] px-3 py-1.5 font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.14em] text-[var(--accent)] transition hover:border-[var(--accent)] hover:bg-[rgba(125,245,212,0.08)] disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isBusy
              ? "Starting…"
              : indexing
                ? "Re-queue ingest"
                : failed
                  ? "Retry ingest"
                  : "Ingest"}
          </button>
        ) : null}

        <button
          type="button"
          disabled={!ready}
          onClick={() => onOpen(repo)}
          title={ready ? "Open review workspace" : "Ingest this repository before opening"}
          className="rounded-md border border-white/10 px-3 py-1.5 font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.14em] text-white/55 transition hover:border-white/25 hover:text-white disabled:cursor-not-allowed disabled:opacity-30"
        >
          Open
        </button>
      </div>
    </div>
  )
}

function SkeletonRows({ count }: { count: number }) {
  return (
    <div className="space-y-0">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="border-b border-white/[0.06] py-3.5">
          <div className="h-3.5 w-48 animate-pulse rounded bg-white/[0.06]" />
          <div className="mt-2 h-3 w-28 animate-pulse rounded bg-white/[0.04]" />
        </div>
      ))}
    </div>
  )
}

export function RepoPicker({ user }: { user: User }) {
  const router = useRouter()
  const [repos, setRepos] = useState<GitHubRepo[]>([])
  const [query, setQuery] = useState("")
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [healthHint, setHealthHint] = useState<string | null>(null)

  async function loadRepos() {
    const data = await api.get<GitHubRepo[]>(endpoints.repos.available())
    setRepos(data)
    return data
  }

  useEffect(() => {
    let cancelled = false

    async function load() {
      setIsLoading(true)
      setError(null)
      try {
        const [data, health] = await Promise.all([
          api.get<GitHubRepo[]>(endpoints.repos.available()),
          api.get<{ status: string; hint?: string | null; redis?: { ok: boolean }; database?: { ok: boolean } }>(
            endpoints.health(),
          ).catch(() => null),
        ])
        if (cancelled) return
        setRepos(data)
        if (health && health.status !== "ok") {
          setHealthHint(
            health.hint ||
              "Backend is degraded — start Docker, API, and the RQ worker (scripts/dev.ps1).",
          )
        } else {
          setHealthHint(null)
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load repositories — is the API running on :8000?",
          )
        }
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [])

  // Poll any processing repos
  useEffect(() => {
    const processing = repos.filter((r) => r.repo_id && r.ingest_status === "processing")
    if (processing.length === 0) return

    let cancelled = false
    const timer = window.setInterval(async () => {
      try {
        const updates = await Promise.all(
          processing.map(async (repo) => {
            const status = await api.get<IngestionStatus>(
              endpoints.repos.ingestStatus(repo.repo_id!),
            )
            return { repoId: repo.repo_id!, status }
          }),
        )
        if (cancelled) return

        setRepos((prev) =>
          prev.map((repo) => {
            const hit = updates.find((u) => u.repoId === repo.repo_id)
            if (!hit) return repo
            return {
              ...repo,
              ingest_status: hit.status.status,
              files_ingested: hit.status.files_ingested,
              ingest_error: hit.status.error_message,
            }
          }),
        )
      } catch {
        // Keep polling; transient errors are fine.
      }
    }, 2000)

    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [repos])

  // All repos the OAuth token can see (owned + collaborator + org).
  const accessibleRepos = useMemo(() => repos, [repos])

  const recent = useMemo(() => {
    const ready = accessibleRepos.filter((r) => r.connected && r.ingest_status === "ready")
    const rest = accessibleRepos.filter((r) => !(r.connected && r.ingest_status === "ready"))
    return [...ready, ...rest].slice(0, 8)
  }, [accessibleRepos])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    const source = accessibleRepos
    if (!q) return source
    return source.filter((repo) => repo.full_name.toLowerCase().includes(q))
  }, [accessibleRepos, query])

  async function ingestRepo(repo: GitHubRepo) {
    setBusyId(repo.repo_id ?? repo.full_name)
    setError(null)
    try {
      let connected: Repo
      if (!repo.connected || !repo.repo_id) {
        connected = await api.post<Repo>(endpoints.repos.connect(), {
          full_name: repo.full_name,
        })
      } else {
        connected = {
          id: repo.repo_id,
          github_repo_id: repo.github_repo_id,
          full_name: repo.full_name,
          default_branch: repo.default_branch,
          ingest_status: repo.ingest_status ?? "pending",
          files_ingested: repo.files_ingested,
          ingest_error: null,
        }
      }

      await api.post<IngestionStatus>(endpoints.repos.startIngest(connected.id))
      await loadRepos()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start ingest")
    } finally {
      setBusyId(null)
    }
  }

  function openRepo(repo: GitHubRepo) {
    if (!(repo.connected && repo.ingest_status === "ready")) return
    const [owner, name] = repo.full_name.split("/")
    if (!owner || !name) return
    router.push(`/repo/${owner}/${name}`)
  }

  return (
    <main className="min-h-dvh bg-[#07080b] text-[#f3f5f0]">
      <header className="border-b border-white/10 bg-[#090a0d]/95 px-4 py-4 backdrop-blur md:px-6">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4">
          <div>
            <Link
              href="/dashboard"
              className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.18em] text-[#9fb8b4] no-underline"
            >
              Meridian
            </Link>
            <h1 className="mt-1 text-xl font-semibold tracking-[-0.02em] text-white md:text-2xl">
              Repositories
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-white/45 sm:inline">@{user.login}</span>
            <SignOutButton />
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-3xl px-4 py-8 md:px-6">
        <p className="mb-6 max-w-2xl text-sm leading-6 text-white/45">
          Ingest a repository before opening it. Meridian indexes the codebase so review
          retrieval has real context. Docker, the API, and the RQ worker must all be running
          — use <span className="font-[family-name:var(--font-mono)] text-white/60">scripts/dev.ps1</span>.
        </p>

        <label className="block">
          <span className="sr-only">Search repositories</span>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search your repositories"
            autoComplete="off"
            className="w-full rounded-md border border-white/10 bg-[#0d0f13] px-4 py-3 font-[family-name:var(--font-mono)] text-sm text-white outline-none placeholder:text-white/30 focus:border-[var(--accent-dim)] focus:ring-1 focus:ring-[var(--accent-dim)]"
          />
        </label>

        {healthHint ? (
          <div className="mb-6 rounded-md border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
            {healthHint}
          </div>
        ) : null}

        {error ? (
          <div className="mt-8 rounded-md border border-rose-400/25 bg-rose-400/10 px-4 py-3 text-sm text-rose-100">
            {error}
          </div>
        ) : null}

        {!error && !query.trim() ? (
          <div className="mt-10">
            <div className="flex items-baseline justify-between gap-3">
              <h2 className="text-sm font-semibold text-white">Recent</h2>
              <span className="font-[family-name:var(--font-mono)] text-[11px] text-white/30">
                Top {Math.min(5, recent.length)}
              </span>
            </div>
            <div className="mt-3 border-t border-white/[0.08]">
              {isLoading ? (
                <SkeletonRows count={5} />
              ) : recent.length === 0 ? (
                <p className="py-6 text-sm text-white/40">No repositories available yet.</p>
              ) : (
                recent.map((repo) => (
                  <RepoRow
                    key={repo.github_repo_id}
                    repo={repo}
                    busyId={busyId}
                    onIngest={ingestRepo}
                    onOpen={openRepo}
                  />
                ))
              )}
            </div>
          </div>
        ) : null}

        <div className="mt-10">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="text-sm font-semibold text-white">
              {query.trim() ? "Results" : "All accessible repositories"}
            </h2>
            {!isLoading ? (
              <span className="font-[family-name:var(--font-mono)] text-[11px] text-white/30">
                {filtered.length}
              </span>
            ) : null}
          </div>
          <div className="mt-3 border-t border-white/[0.08]">
            {isLoading ? (
              <SkeletonRows count={8} />
            ) : filtered.length === 0 ? (
              <p className="py-6 text-sm text-white/40">
                {query.trim()
                  ? `No repositories match "${query.trim()}".`
                  : "No repositories found for this GitHub account."}
              </p>
            ) : (
              filtered.map((repo) => (
                <RepoRow
                  key={repo.github_repo_id}
                  repo={repo}
                  busyId={busyId}
                  onIngest={ingestRepo}
                  onOpen={openRepo}
                />
              ))
            )}
          </div>
        </div>
      </section>
    </main>
  )
}
