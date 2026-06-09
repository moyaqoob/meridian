import NextAuth from "next-auth"
import type { AuthOptions } from "next-auth"
import GitHub from "next-auth/providers/github"


export const authOptions: AuthOptions = {
  providers: [
    GitHub({
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
    }),
  ],
  secret: process.env.NEXTAUTH_SECRET!,
}


const handler = NextAuth(authOptions)

export { handler as GET, handler as POST }
