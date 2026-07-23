export function BackgroundGrid() {
  return (
    <div
      aria-hidden="true"
      className="-z-10 fixed inset-0 pointer-events-none"
      style={{
        // Use theme foreground with very low emphasis for scanline/grid vibe
        backgroundImage: `
          repeating-linear-gradient(
            0deg,
            color-mix(in oklab, var(--color-foreground) 6%, transparent) 0px,
            color-mix(in oklab, var(--color-foreground) 6%, transparent) 1px,
            transparent 1px,
            transparent 24px
          ),
          repeating-linear-gradient(
            90deg,
            color-mix(in oklab, var(--color-foreground) 6%, transparent) 0px,
            color-mix(in oklab, var(--color-foreground) 6%, transparent) 1px,
            transparent 1px,
            transparent 24px
          )
        `,
        opacity: 0.25,
      }}
    />
  )
}
