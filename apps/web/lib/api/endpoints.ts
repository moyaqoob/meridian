export const endpoints = {
  auth: {
    github: () => "/api/auth/github",
    me: () => "/api/auth/me",
    logout: () => "/api/auth/logout",
  },
  repos: {
    list: () => "/api/repos/",
    available: () => "/api/repos/available",
    connect: () => "/api/repos/connect",
  },
  prs: {
    list: (owner: string, repo: string) => `/api/prs/${owner}/${repo}`,
    detail: (owner: string, repo: string, number: number) =>
      `/api/prs/${owner}/${repo}/${number}`,
  },
} as const
