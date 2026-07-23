import { BackgroundGrid } from "@/components/background-grid"
import { FloatingSymbols } from "@/components/floating-symbols"
import { HeroTitle } from "@/components/hero-title"
import CustomCursor from "@/components/custom-cursor"
import ThemeToggle from "@/components/theme-toggle"
import { AccessModal } from "@/components/access-modal"

export default function Home() {
  return (
    <main className="relative min-h-screen flex flex-col overflow-hidden">
      <ThemeToggle />
      <CustomCursor />
      {/* Background */}
      <BackgroundGrid />

      {/* Header (optional placeholder for future nav) */}
      <header className="sr-only">
        <h1>Code Crafter</h1>
      </header>

      {/* Hero */}
      <section className="flex-1 flex items-center justify-center relative px-6" aria-label="Hero">
        <div className="max-w-3xl w-full text-center relative [perspective:800px]">
          <div className="relative">
            <div className="relative z-10">
              <HeroTitle />
            </div>
            <FloatingSymbols />
          </div>

          <p className="mt-6 text-muted-foreground font-mono leading-relaxed text-pretty">
            {"An Agentic AI for Autonomous Code Development and Debugging"}
          </p>

          <div className="mt-10 flex items-center justify-center">
            <AccessModal />
          </div>
        </div>
      </section>

      {/* Signature */}
      {/* Removed entire signature block that was fixed at bottom-left */}
    </main>
  )
}
