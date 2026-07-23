export function HeroTitle() {
  return (
    <h2
      id="code-crafter-title"
      className="text-5xl md:text-7xl font-mono font-extrabold tracking-tight text-center select-none"
      aria-label="Code Crafter"
    >
      <span className="inline-block">
        {"Code "}
        <span className="text-primary title-glow">{"Crafter"}</span>
      </span>
      <span className="ml-2 text-primary animate-caret-blink" aria-hidden="true">
        {"▌"}
      </span>
    </h2>
  )
}
