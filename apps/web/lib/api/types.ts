export type GitHubRepo = {
  github_repo_id: number
  full_name: string
  default_branch: string
  private: boolean
  connected: boolean
}

export type Repo = {
  id: string
  github_repo_id: number
  full_name: string
  default_branch: string
  ingest_status: "pending" | "processing" | "ready" | "failed"
  files_ingested: number | null
  ingest_error: string | null
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

export type DiffLineType = "add" | "del" | "ctx" | "meta" | "same"

export type DiffLine = {
  type: DiffLineType
  text: string
  oldLine: number | null
  newLine: number | null
}
