"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { SignOutButton } from "@/components/auth-buttons"
import { api } from "@/lib/api/client"
import { endpoints } from "@/lib/api/endpoints"
import type { GitHubRepo } from "@/lib/api/types"
import type { User } from "@/lib/auth/session"

function RepoRow({
  repo,
  onSelect,
}: {
  repo: GitHubRepo
  onSelect: (repo: GitHubRepo) => void
}) {
  const [owner, name] = repo.full_name.split("/")

  return (
    <button
      type="button"
      onClick={() => onSelect(repo)}
      className="group flex w-full items-center justify-between gap-4 border-b border-white/[0.06] px-1 py-3.5 text-left transition hover:bg-white/[0.03] active:translate-y-px"
    >
      <div className="min-w-0">
        <p className="truncate font-[family-name:var(--font-mono)] text-[13px] text-white/90">
          <span className="text-white/40">{owner}/</span>
          {name}
        </p>
        <p className="mt-1 text-[12px] text-white/35">
          {repo.private ? "Private" : "Public"} · {repo.default_branch}
          {repo.connected ? " · Connected" : ""}
        </p>
      </div>
      <span className="shrink-0 font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.14em] text-white/25 transition group-hover:text-[var(--accent)]">
        Open
      </span>
    </button>
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

  useEffect(() => {
    let cancelled = false

    async function load() {
      setIsLoading(true)
      setError(null)
      try {
        const data = await api.get<GitHubRepo[]>(endpoints.repos.available())
        if (!cancelled) setRepos(data)
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load repositories")
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

  const ownedRepos = useMemo(
    () => repos.filter((repo) => repo.full_name.startsWith(`${user.login}/`)),
    [repos, user.login],
  )

  const recent = useMemo(() => ownedRepos.slice(0, 5), [ownedRepos])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return ownedRepos
    return ownedRepos.filter((repo) => repo.full_name.toLowerCase().includes(q))
  }, [ownedRepos, query])

  async function openRepo(repo: GitHubRepo) {
    const [owner, name] = repo.full_name.split("/")
    if (!owner || !name) return

    try {
      if (!repo.connected) {
        await api.post(endpoints.repos.connect(), { full_name: repo.full_name })
      }
    } catch {
      // Viewing PRs only needs the session token; connect is best-effort.
    }

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
                <p className="py-6 text-sm text-white/40">No owned repositories yet.</p>
              ) : (
                recent.map((repo) => (
                  <RepoRow key={repo.github_repo_id} repo={repo} onSelect={openRepo} />
                ))
              )}
            </div>
          </div>
        ) : null}

        <div className="mt-10">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="text-sm font-semibold text-white">
              {query.trim() ? "Results" : "Your repositories"}
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
                  : "No owned repositories found for this account."}
              </p>
            ) : (
              filtered.map((repo) => (
                <RepoRow key={repo.github_repo_id} repo={repo} onSelect={openRepo} />
              ))
            )}
          </div>
        </div>

        {!isLoading && ownedRepos.length === 0 && !error ? (
          <p className="mt-8 text-sm leading-6 text-white/40">
            Showing repositories owned by <span className="text-white/60">@{user.login}</span>.
            Sign in with a GitHub account that has repos, then refresh.
          </p>
        ) : null}
      </section>
    </main>
  )
}
