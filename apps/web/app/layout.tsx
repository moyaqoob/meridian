import type { Metadata } from "next"
import localFont from "next/font/local"
import "./globals.css"

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-sans",
  display: "swap",
})

const geistDisplay = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-display",
  display: "swap",
})

const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-mono",
  display: "swap",
})

export const metadata: Metadata = {
  title: "Meridian - Code review that knows the whole map",
  description:
    "Meridian traces every change through the repo it lives in: call sites, dependents, and the code your reviewers did not have time to reopen.",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistDisplay.variable} ${geistMono.variable}`}
      >
        {children}
      </body>
    </html>
  )
}
