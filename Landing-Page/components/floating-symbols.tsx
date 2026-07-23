"use client"

import type React from "react"
import { useMemo, useState, useCallback, useEffect } from "react"

type SymbolState = {
  tx: number
  ty: number
  scale: number
  rx: number
  ry: number
}

type OrbitSpec = {
  char: string
  color: string
  radius: number // px radius from title center
  duration: number // seconds
  angle: number // initial angle (deg)
  dir: "normal" | "reverse" // spin direction
  sizeClass: string
  tiltX: number
  tiltY: number
  delay: string
}

const COLORS = [
  "oklch(0.62 0.12 254)", // blue
  "oklch(0.72 0.11 220)", // cyan
  "oklch(0.75 0.13 160)", // teal/green
  "oklch(0.72 0.16 35)", // orange
  "oklch(0.75 0.18 330)", // pink/magenta
]

const CHARS = ["{", "}", "<", "/>", "=>", "()", "[]", "λ", "::"]

const rand = (min: number, max: number) => Math.random() * (max - min) + min
const pick = <T,>(arr: T[], i: number) => arr[i % arr.length]

export function FloatingSymbols() {
  // track center of title and a safe radius (never overlap/approach)
  const [center, setCenter] = useState<{ x: number; y: number; safe: number; ready: boolean }>({
    x: 0,
    y: 0,
    safe: 140,
    ready: false,
  })

  // measure title center + safe radius
  useEffect(() => {
    const el = document.getElementById("code-crafter-title")
    if (!el) return

    const compute = () => {
      const r = el.getBoundingClientRect()
      // center in viewport coordinates (since container is fixed)
      const x = r.left + r.width / 2
      const y = r.top + r.height / 2
      // safe radius: half-diagonal of title plus padding
      const halfDiag = Math.hypot(r.width, r.height) / 2
      const safe = halfDiag + 28 // keeps symbols from getting close
      setCenter({ x, y, safe, ready: true })
    }

    compute()

    const handle = () => compute()
    window.addEventListener("resize", handle, { passive: true })
    window.addEventListener("scroll", handle, { passive: true })

    // ResizeObserver to react to title size changes
    let ro: ResizeObserver | null = null
    if ("ResizeObserver" in window) {
      ro = new ResizeObserver(() => compute())
      ro.observe(el)
    }

    return () => {
      window.removeEventListener("resize", handle)
      window.removeEventListener("scroll", handle)
      if (ro) ro.disconnect()
    }
  }, [])

  // build per-symbol orbit specs; randomized but respects safe radius
  const specs: OrbitSpec[] = useMemo(() => {
    const count = CHARS.length // keep current count as user liked size/qty
    return Array.from({ length: count }).map((_, i) => {
      const char = CHARS[i]
      const color = pick(COLORS, i)
      // symbols never enter the safe radius; add extra distance for separation
      const minR = center.safe + 60
      const maxR = minR + 140
      const radius = rand(minR, maxR)
      const duration = rand(20, 36) // seconds
      const angle = rand(0, 360)
      const dir: OrbitSpec["dir"] = i % 2 === 0 ? "normal" : "reverse"
      const sizeClass = "text-xl md:text-2xl" // baseline +35% already applied previously
      const tiltX = i % 2 === 0 ? -8 : 6
      const tiltY = i % 3 === 0 ? 9 : -7
      const delay = `${rand(-duration, 0)}s`
      return { char, color, radius, duration, angle, dir, sizeClass, tiltX, tiltY, delay }
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [center.safe]) // recompute if title size changes; keep random stable otherwise

  const [states, setStates] = useState<Record<number, SymbolState>>({})

  const handleEnter = useCallback((i: number) => {
    setStates((prev) => ({
      ...prev,
      [i]: { tx: 0, ty: -8, scale: 1.65, rx: -8, ry: 8 },
    }))
  }, [])

  const handleLeave = useCallback((i: number) => {
    setStates((prev) => ({
      ...prev,
      [i]: { tx: 0, ty: 0, scale: 1.35, rx: 0, ry: 0 },
    }))
  }, [])

  const handleMove = useCallback((i: number, e: React.PointerEvent<HTMLSpanElement>) => {
    const rect = (e.currentTarget as HTMLSpanElement).getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    const dx = (e.clientX - cx) / 10
    const dy = (e.clientY - cy) / 10
    setStates((prev) => ({
      ...prev,
      [i]: {
        tx: dx,
        ty: dy,
        scale: 1.55,
        rx: -dy * 1.2,
        ry: dx * 1.2,
      },
    }))
  }, [])

  return (
    <div
      className="fixed inset-0 z-0 pointer-events-none"
      aria-hidden="true"
      style={{
        transformStyle: "preserve-3d",
        // hide initial jank until we measure center
        opacity: center.ready ? 1 : 0,
        transition: "opacity 200ms ease",
      }}
    >
      {/* Centered origin anchored to title center */}
      <div
        className="absolute"
        style={{
          left: `${center.x}px`,
          top: `${center.y}px`,
          width: 0,
          height: 0,
          // this is the actual orbit center point
        }}
      >
        {specs.map((s, i) => {
          const st = states[i] ?? { tx: 0, ty: 0, scale: 1.35, rx: s.tiltX, ry: s.tiltY }
          const popTransform = `translate3d(${st.tx}px, ${st.ty}px, 0) rotateX(${st.rx}deg) rotateY(${st.ry}deg) scale(${st.scale})`
          return (
            <div
              key={i}
              className="absolute"
              style={{
                animationName: "orbit",
                animationDuration: `${s.duration}s`,
                animationTimingFunction: "linear",
                animationIterationCount: "infinite",
                animationDirection: s.dir,
                animationDelay: s.delay,
                transformOrigin: "0 0",
              }}
            >
              <span
                className={[
                  "absolute pointer-events-auto select-none will-change-transform transition-transform duration-300 ease-out",
                  s.sizeClass,
                  "font-mono",
                ].join(" ")}
                style={{
                  // place symbol at its orbit radius and initial angle
                  transform: `rotate(${s.angle}deg) translateX(${s.radius}px) rotate(${-s.angle}deg) ${popTransform}`,
                  color: s.color,
                  textShadow: `0 1px 0 rgba(0,0,0,.06)`,
                  cursor: "inherit",
                }}
                onPointerEnter={() => handleEnter(i)}
                onPointerLeave={() => handleLeave(i)}
                onPointerMove={(e) => handleMove(i, e)}
                onPointerDown={() => handleEnter(i)}
                onPointerUp={() => handleLeave(i)}
              >
                {s.char}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
