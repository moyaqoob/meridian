"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import Link from "next/link"
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react"
import dagre from "dagre"
import "@xyflow/react/dist/style.css"

import { SignOutButton } from "@/components/auth-buttons"
import { api } from "@/lib/api/client"
import { endpoints } from "@/lib/api/endpoints"
import type { FileChunk, GraphNode, RepoGraph } from "@/lib/api/types"

type FileNodeData = {
  label: string
  language: string
  loc: number
  chunkCount: number
  externalDeps: number
  size: number
}

function languageColor(language: string): string {
  if (language === "python") return "#7dd3fc"
  if (language === "typescript" || language === "javascript") return "#86efac"
  if (language === "rust") return "#fdba74"
  return "#cbd5e1"
}

function FileNode({ data, selected }: NodeProps) {
  const d = data as FileNodeData
  const color = languageColor(d.language)
  return (
    <div
      className={`rounded-md border px-3 py-2 shadow-sm transition ${
        selected
          ? "border-[var(--accent)] bg-[#0f1614]"
          : "border-white/15 bg-[#0c0e12]"
      }`}
      style={{ minWidth: 140 + d.size * 20 }}
    >
      <Handle type="target" position={Position.Left} className="!bg-white/40" />
      <p
        className="max-w-[220px] truncate font-[family-name:var(--font-mono)] text-[11px] text-white"
        title={d.label}
      >
        {d.label.split("/").pop()}
      </p>
      <p className="mt-1 font-[family-name:var(--font-mono)] text-[10px] text-white/40">
        <span style={{ color }}>{d.language}</span>
        {" · "}
        {d.loc} loc · {d.chunkCount} chunks
        {d.externalDeps > 0 ? ` · ${d.externalDeps} ext` : ""}
      </p>
      <Handle type="source" position={Position.Right} className="!bg-white/40" />
    </div>
  )
}

const nodeTypes = { file: FileNode }

function layoutGraph(graph: RepoGraph): { nodes: Node[]; edges: Edge[] } {
  const maxLoc = Math.max(1, ...graph.nodes.map((n) => n.loc))
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: "LR", nodesep: 40, ranksep: 80 })

  const rfNodes: Node[] = graph.nodes.map((n) => {
    const size = Math.min(3, Math.max(0, n.loc / maxLoc))
    const width = 160 + size * 30
    const height = 56
    g.setNode(n.id, { width, height })
    return {
      id: n.id,
      type: "file",
      position: { x: 0, y: 0 },
      data: {
        label: n.id,
        language: n.language,
        loc: n.loc,
        chunkCount: n.chunk_count,
        externalDeps: n.external_deps,
        size,
      } satisfies FileNodeData,
      style: { width, height },
    }
  })

  const rfEdges: Edge[] = graph.edges.map((e, i) => {
    g.setEdge(e.source, e.target)
    return {
      id: `e-${i}-${e.source}-${e.target}`,
      source: e.source,
      target: e.target,
      type: "smoothstep",
      animated: e.type === "reexport",
      style: { stroke: "rgba(125,245,212,0.35)" },
      markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(125,245,212,0.55)" },
    }
  })

  dagre.layout(g)

  for (const node of rfNodes) {
    const pos = g.node(node.id)
    const width = Number(node.style?.width ?? 160)
    const height = Number(node.style?.height ?? 56)
    node.position = { x: pos.x - width / 2, y: pos.y - height / 2 }
  }

  return { nodes: rfNodes, edges: rfEdges }
}

export function StructureGraph({
  owner,
  repo,
  repoId,
}: {
  owner: string
  repo: string
  repoId: string
}) {
  const [graph, setGraph] = useState<RepoGraph | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<GraphNode | null>(null)
  const [chunks, setChunks] = useState<FileChunk[]>([])
  const [chunksLoading, setChunksLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const data = await api.get<RepoGraph>(endpoints.repos.graph(repoId))
        if (!cancelled) setGraph(data)
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load graph")
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [repoId])

  const layout = useMemo(() => (graph ? layoutGraph(graph) : null), [graph])

  const onNodeClick = useCallback(
    async (_: unknown, node: Node) => {
      const meta = graph?.nodes.find((n) => n.id === node.id) ?? null
      setSelected(meta)
      setChunks([])
      if (!meta) return
      setChunksLoading(true)
      try {
        const rows = await api.get<FileChunk[]>(
          endpoints.repos.fileChunks(repoId, meta.id),
        )
        setChunks(rows)
      } catch {
        setChunks([])
      } finally {
        setChunksLoading(false)
      }
    },
    [graph, repoId],
  )

  const largeRepo = (graph?.nodes.length ?? 0) > 250

  return (
    <main className="flex h-dvh flex-col overflow-hidden bg-[#07080b] text-[#f3f5f0]">
      <header className="flex shrink-0 items-center justify-between gap-4 border-b border-white/10 bg-[#090a0d] px-4 py-3 md:px-5">
        <div className="min-w-0">
          <Link
            href={`/repo/${owner}/${repo}`}
            className="font-[family-name:var(--font-mono)] text-[11px] text-white/35 no-underline transition hover:text-white/60"
          >
            ← Review workspace
          </Link>
          <h1 className="mt-0.5 truncate font-[family-name:var(--font-mono)] text-base font-semibold tracking-[-0.02em] text-white md:text-lg">
            Structure · <span className="text-white/40">{owner}/</span>
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

      {largeRepo ? (
        <div className="shrink-0 border-b border-amber-400/20 bg-amber-400/10 px-4 py-2 text-sm text-amber-100">
          This repo has {graph?.nodes.length} files — a flat graph may be hard to read.
          Directory collapse is planned for v1.5.
        </div>
      ) : null}

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px]">
        <section className="relative min-h-0 border-b border-white/10 lg:border-b-0 lg:border-r">
          {loading || !layout ? (
            <div className="flex h-full items-center justify-center text-sm text-white/40">
              {loading ? "Loading structure…" : "No graph data yet — re-ingest the repo."}
            </div>
          ) : (
            <ReactFlow
              nodes={layout.nodes}
              edges={layout.edges}
              nodeTypes={nodeTypes}
              fitView
              minZoom={0.2}
              onNodeClick={onNodeClick}
              proOptions={{ hideAttribution: true }}
            >
              <Background color="#ffffff10" gap={24} />
              <Controls className="!bg-[#101217] !border-white/10 !shadow-none" />
              <MiniMap
                className="!bg-[#101217] !border-white/10"
                nodeColor={() => "#7df5d4"}
                maskColor="rgba(0,0,0,0.6)"
              />
            </ReactFlow>
          )}
        </section>

        <aside className="min-h-0 overflow-auto bg-[#0c0e12] p-4">
          {!selected ? (
            <p className="text-sm leading-6 text-white/40">
              Click a file node to inspect its indexed chunks.
            </p>
          ) : (
            <div>
              <p className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.14em] text-white/35">
                File
              </p>
              <h2 className="mt-1 break-all font-[family-name:var(--font-mono)] text-sm text-white">
                {selected.id}
              </h2>
              <p className="mt-2 font-[family-name:var(--font-mono)] text-[12px] text-white/45">
                {selected.language} · {selected.loc} loc · {selected.chunk_count} chunks
                {selected.external_deps > 0
                  ? ` · ${selected.external_deps} external deps`
                  : ""}
              </p>

              <div className="mt-6 space-y-3">
                {chunksLoading ? (
                  <p className="text-sm text-white/40">Loading chunks…</p>
                ) : chunks.length === 0 ? (
                  <p className="text-sm text-white/40">No chunks indexed for this file.</p>
                ) : (
                  chunks.map((chunk) => (
                    <article
                      key={chunk.id}
                      className="rounded-md border border-white/10 bg-white/[0.03] p-3"
                    >
                      <p className="font-[family-name:var(--font-mono)] text-[11px] text-white/40">
                        L{chunk.start_line}–{chunk.end_line}
                      </p>
                      <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap font-[family-name:var(--font-mono)] text-[11px] leading-5 text-white/70">
                        {chunk.content.slice(0, 1200)}
                        {chunk.content.length > 1200 ? "…" : ""}
                      </pre>
                    </article>
                  ))
                )}
              </div>
            </div>
          )}
        </aside>
      </div>
    </main>
  )
}
