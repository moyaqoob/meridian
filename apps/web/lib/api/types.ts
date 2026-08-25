export type IngestStatus = "pending" | "processing" | "ready" | "failed"

export type GitHubRepo = {
  github_repo_id: number
  full_name: string
  default_branch: string
  private: boolean
  connected: boolean
  repo_id: string | null
  ingest_status: IngestStatus | null
  files_ingested: number | null
  ingest_error: string | null
}

export type Repo = {
  id: string
  github_repo_id: number
  full_name: string
  default_branch: string
  ingest_status: IngestStatus
  files_ingested: number | null
  ingest_error: string | null
}

export type IngestionStatus = {
  repo_id: string
  status: IngestStatus
  files_ingested: number | null
  error_message: string | null
}

export type PullRequest = {
  number: number
  title: string
  state: string
  author: string
  html_url: string
  updated_at: string
  base_branch: string
  head_branch: string
  additions: number
  deletions: number
  changed_files: number
}

export type PullFile = {
  filename: string
  status: string
  additions: number
  deletions: number
}

export type PullRequestDetail = PullRequest & {
  body: string | null
  diff: string
  files: PullFile[]
}

export type ReviewFinding = {
  id: string
  severity: "high" | "medium" | "low"
  category: string
  title: string
  comment: string
  file_path: string | null
  chunk_ref: string | null
}

export type ReviewOut = {
  review_id: string
  pr_id: string
  summary: string
  pr_type: "feat" | "fix" | "refactor" | "chore"
  findings: ReviewFinding[]
  model_version: string
  timings: Record<string, number>
}

export type ReviewJob = {
  status: "queued" | "exists" | "running" | "complete" | "error"
  review_id: string | null
  pr_id: string | null
  head_sha: string
  message: string
  review: ReviewOut | null
}

export type StageUpdateEvent = {
  stage: "validation" | "retrieval" | "generation" | "citation-mapping" | "complete"
  progress: number
  message: string
  duration_ms?: number
}

export type GraphNode = {
  id: string
  language: string
  loc: number
  chunk_count: number
  external_deps: number
}

export type GraphEdge = {
  source: string
  target: string
  type: "import" | "reexport"
}

export type RepoGraph = {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export type FileChunk = {
  id: string
  file_path: string
  start_line: number
  end_line: number
  language: string
  content: string
}

export type DiffLineType = "add" | "del" | "ctx" | "meta" | "same"

export type DiffLine = {
  type: DiffLineType
  text: string
  oldLine: number | null
  newLine: number | null
}
