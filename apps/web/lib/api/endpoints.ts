export const endpoints = {
  health: () => "/api/health",
  auth: {
    github: () => "/api/auth/github",
    me: () => "/api/auth/me",
    logout: () => "/api/auth/logout",
  },
  repos: {
    list: () => "/api/repos/",
    available: () => "/api/repos/available",
    connect: () => "/api/repos/connect",
    startIngest: (repoId: string) => `/api/repos/${repoId}/ingest`,
    ingestStatus: (repoId: string) => `/api/repos/${repoId}/ingest`,
    graph: (repoId: string) => `/api/repos/${repoId}/graph`,
    fileChunks: (repoId: string, filePath: string) =>
      `/api/repos/${repoId}/chunks?file_path=${encodeURIComponent(filePath)}`,
  },
  prs: {
    list: (owner: string, repo: string) => `/api/prs/${owner}/${repo}`,
    detail: (owner: string, repo: string, number: number) =>
      `/api/prs/${owner}/${repo}/${number}`,
    review: (owner: string, repo: string, number: number) =>
      `/api/prs/${owner}/${repo}/${number}/review`,
    reviewStatus: (owner: string, repo: string, number: number, headSha?: string) => {
      const base = `/api/prs/${owner}/${repo}/${number}/review`
      return headSha ? `${base}?head_sha=${encodeURIComponent(headSha)}` : base
    },
  },
  review: {
    stream: (reviewId: string) => `/api/pr/${reviewId}/review/stream`,
  },
} as const
