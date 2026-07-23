"use client"

import { useEffect, useState } from "react"

export default function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">("light")

  useEffect(() => {
    const stored = (localStorage.getItem("theme") as "light" | "dark") || null
    const prefersDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches
    const next = stored ?? (prefersDark ? "dark" : "light")
    setTheme(next)
    document.documentElement.classList.toggle("dark", next === "dark")
  }, [])

  const toggle = () => {
    const next = theme === "light" ? "dark" : "light"
    setTheme(next)
    document.documentElement.classList.toggle("dark", next === "dark")
    localStorage.setItem("theme", next)
  }

  return (
    <button
      type="button"
      aria-label="Toggle theme"
      onClick={toggle}
      className="absolute right-4 top-4 z-[65] rounded-full border border-[color:var(--border)] bg-[color:var(--card)] px-3 py-2 text-sm text-[color:var(--foreground)] shadow-sm hover:opacity-90 cursor-none"
    >
      {theme === "dark" ? "Light" : "Dark"}
    </button>
  )
}
