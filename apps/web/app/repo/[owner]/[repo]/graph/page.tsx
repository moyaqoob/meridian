"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { StructureGraph } from "@/components/graph/structure-graph"
import { api } from "@/lib/api/client"
import { endpoints } from "@/lib/api/endpoints"

export default function RepoGraphPage({
  params,
}: {
  params: Promise<{ owner: string; repo: string }>
}) {
  const router = useRouter()
  const [owner, setOwner] = useState("")
  const [repo, setRepo] = useState("")
  const [repoId, setRepoId] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function boot() {
      const { owner: o, repo: r } = await params
      if (cancelled) return
      setOwner(o)
      setRepo(r)
      try {
        const available = await api.get<
          Array<{
            full_name: string
            connected: boolean
            ingest_status: string | null
            repo_id: string | null
          }>
        >(endpoints.repos.available())
        if (cancelled) return
        const hit = available.find((row) => row.full_name === `${o}/${r}`)
        if (!hit?.connected || hit.ingest_status !== "ready" || !hit.repo_id) {
          router.replace("/dashboard")
          return
        }
        setRepoId(hit.repo_id)
      } catch {
        router.replace("/dashboard")
      }
    }
    void boot()
    return () => {
      cancelled = true
    }
  }, [params, router])

  if (!repoId || !owner || !repo) {
    return (
      <main className="flex h-dvh items-center justify-center bg-[#07080b] text-sm text-white/40">
        Loading structure…
      </main>
    )
  }

  return <StructureGraph owner={owner} repo={repo} repoId={repoId} />
}
