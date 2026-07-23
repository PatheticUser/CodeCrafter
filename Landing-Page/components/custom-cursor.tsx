"use client"

import { useEffect, useRef, useState } from "react"

export default function CustomCursor() {
  const ref = useRef<HTMLDivElement | null>(null)
  const target = useRef({ x: 0, y: 0 })
  const pos = useRef({ x: 0, y: 0 })
  const [down, setDown] = useState(false)

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      target.current.x = e.clientX
      target.current.y = e.clientY
    }
    const onTouch = (e: TouchEvent) => {
      if (e.touches && e.touches[0]) {
        target.current.x = e.touches[0].clientX
        target.current.y = e.touches[0].clientY
      }
    }
    const onDown = () => setDown(true)
    const onUp = () => setDown(false)

    window.addEventListener("mousemove", onMove)
    window.addEventListener("touchmove", onTouch, { passive: true })
    window.addEventListener("mousedown", onDown)
    window.addEventListener("mouseup", onUp)
    window.addEventListener("touchstart", onDown)
    window.addEventListener("touchend", onUp)

    let raf = 0
    const tick = () => {
      pos.current.x += (target.current.x - pos.current.x) * 0.18
      pos.current.y += (target.current.y - pos.current.y) * 0.18
      if (ref.current) {
        ref.current.style.transform = `translate3d(${pos.current.x}px, ${pos.current.y}px, 0) scale(${down ? 0.9 : 1})`
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener("mousemove", onMove)
      window.removeEventListener("touchmove", onTouch)
      window.removeEventListener("mousedown", onDown)
      window.removeEventListener("mouseup", onUp)
      window.removeEventListener("touchstart", onDown)
      window.removeEventListener("touchend", onUp)
    }
  }, [down])

  const size = 28

  return (
    <div
      ref={ref}
      aria-hidden="true"
      className="pointer-events-none fixed left-0 top-0 z-[60] -translate-x-1/2 -translate-y-1/2"
      style={{
        filter:
          "drop-shadow(0 0 4px var(--cursor-glow)) drop-shadow(0 0 10px var(--cursor-glow)) drop-shadow(0 0 18px var(--cursor-glow))",
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 100 100"
        className="transition-transform duration-200 ease-out"
        style={{ transform: "rotate(15deg)" }}
      >
        <polygon
          points="50,5 93,28 93,72 50,95 7,72 7,28"
          fill="none"
          stroke="var(--cursor)"
          strokeWidth="6"
          strokeLinejoin="round"
        />
        <path d="M50 20 L70 30 L70 50" fill="none" stroke="var(--cursor)" strokeWidth="6" strokeLinecap="round" />
        <circle cx="50" cy="50" r="4" fill="var(--cursor)" />
      </svg>
    </div>
  )
}
