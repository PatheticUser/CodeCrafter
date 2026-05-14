# Phase 3 — Frontend (DESIGN.md-Driven)

> **Effort:** ~5 days · **Dependencies:** Phase 2  
> **Goal:** Build a web UI that faithfully implements the DESIGN.md editorial design system — cream canvas, coral accents, serif headlines, dark product surfaces. Vite + React + vanilla CSS.

---

## 3.1 Technology Decisions

### Why Vite + React + Vanilla CSS

- **Vite** — fastest dev server, instant HMR, optimized production builds. No Webpack configuration hell.
- **React** — component model maps cleanly to DESIGN.md's component definitions. Each design component becomes a React component.
- **Vanilla CSS** — DESIGN.md defines a complete design system with specific pixel values, colors, and typography. CSS custom properties (variables) translate the YAML tokens directly. No need for Tailwind — it would fight the design system rather than serve it.
- **No UI library** — no Material UI, no Chakra, no shadcn. DESIGN.md defines its own component language. Using a third-party library would impose conflicting design opinions.

### Why NOT Tailwind
DESIGN.md specifies exact values: `#cc785c` for primary, `8px` for button radius, `Copernicus` serif at weight 400 with `-1.5px` letter-spacing. Tailwind's utility classes would require extensive customization to match these, and the resulting `className` strings would be harder to maintain than a clean CSS file with custom properties.

---

## 3.2 Project Setup

### What To Do

1. **Scaffold with Vite** — run the create-vite script in the project's `frontend/` directory. Use the React template (not TypeScript for now — keeps iteration fast).

2. **Install routing** — `react-router-dom` for client-side navigation between landing page, login, and chat workspace.

3. **Configure Vite proxy** — in `vite.config.js`, proxy `/api/*` and `/auth/*` to `http://localhost:8000` (the FastAPI server). Proxy WebSocket paths too. This eliminates CORS issues during development.

4. **Remove Vite's default styles** — delete the boilerplate CSS and demo components. Start from scratch with the design system.

---

## 3.3 Design Token Translation

### What To Do

DESIGN.md defines tokens in YAML format. Translate every token into CSS custom properties in a `tokens.css` file.

1. **Colors** — every color from DESIGN.md becomes a `--color-*` variable. Use the exact hex values specified. The naming should mirror DESIGN.md's naming: `--color-primary`, `--color-canvas`, `--color-surface-dark`, etc.

2. **Typography** — DESIGN.md specifies Copernicus (licensed) with Cormorant Garamond as the open-source substitute. Import from Google Fonts:
   - Cormorant Garamond (weight 400, 500) — replaces Copernicus for display headlines
   - Inter (weight 400, 500) — replaces StyreneB for body text
   - JetBrains Mono (weight 400) — for code blocks
   
   Define typography classes matching DESIGN.md tokens: `.display-xl`, `.display-lg`, `.body-md`, `.code`, etc.

3. **Spacing** — translate the spacing scale (`xxs` through `section`) into `--space-*` variables.

4. **Border radius** — translate into `--rounded-*` variables.

5. **Add transitions and shadows** — DESIGN.md mentions subtle hover states and rare shadows. Define `--shadow-subtle` and `--transition-fast/normal` variables.

### Critical Design Rules (from DESIGN.md)

- **Canvas is cream, NEVER white** — `#faf9f5` is the page floor. Pure white (`#fff`) must never appear as a background.
- **Display headlines are ALWAYS serif** — Cormorant Garamond at weight 400 with negative letter-spacing. Using Inter/sans-serif for headlines is a brand violation.
- **Coral is scarce** — only on primary CTAs and full-bleed callout cards. Don't paint every accent element coral.
- **Dark surfaces show product chrome** — code blocks, terminal output, model cards use dark navy backgrounds. This is where the product lives.
- **Surface rhythm alternates** — cream → cream-card → dark → cream → coral-callout → dark-footer. Never repeat the same surface in consecutive sections.
- **Headlines stay weight 400** — never bold the serif display font. Weight 700 on Copernicus/Cormorant reads as bombastic and off-brand.

---

## 3.4 Component Architecture

### Components to Build

Build each component to match its DESIGN.md definition exactly. Every component references design tokens, never hardcoded values.

**Navigation:**
- **TopNav** — cream background, 64px height. Left: brand wordmark. Center-left: navigation links. Right: "New Chat" coral button + user dropdown. Links use `nav-link` typography (14px/500 sans). Collapses to hamburger below 768px.

**Chat Interface:**
- **ChatPanel** — the main workspace. Split layout: session sidebar on left (dark surface, 300px), chat area on right. Messages flow vertically with auto-scroll.
- **MessageBubble** — user messages get cream card background (`surface-card`). Agent messages get dark background (`surface-dark`) with cream text. Both use `body-md` typography. Include timestamp in `caption` style.
- **ToolCallCard** — displayed inline in the message flow when the agent executes tools. Dark surface card with `rounded-lg`. Header shows tool name + icon. Body shows a brief argument summary. Result shows success (teal dot) or error (red dot). Click to expand full details. Use `code` typography for arguments.
- **CodeBlock** — dark background (`surface-dark-soft`), JetBrains Mono font, line numbers in `muted-soft` color. Copy button in top-right corner using `button-icon-circular` style. Language name shown as a `badge-pill`. Horizontal scroll for long lines — never wrap code.
- **InputBar** — full-width text input at bottom of chat area. `canvas` background with `hairline` border. Focus state: border changes to `primary` (coral) with a subtle outer ring. Send button on right in `button-primary` style (coral). Shift+Enter for newline, Enter to send.
- **Spinner** — loading indicator while agent is processing. Subtle, on-brand animation using coral color.

**Session Management:**
- **SessionSidebar** — dark surface background. Lists sessions with name and last-modified timestamp. Active session has coral left border accent. "New Session" button at top. Inactive sessions show message count in `on-dark-soft` color. Swipe-to-delete on mobile, icon button on desktop.

**Workspace:**
- **WorkspaceTree** — collapsible file tree showing the user's workspace contents. Dark surface card style. Folder/file icons. Click to view file content.
- **ModelSelector** — dropdown in the top nav showing available Ollama models. Current model shown as a `badge-pill`. Click to switch. Model capabilities shown in `caption` text.

**Shared:**
- **Button** — primary (coral bg, white text, `rounded-md`) and secondary (canvas bg, ink text, hairline border) variants. 40px height, 12px × 20px padding. Active state darkens primary to `primary-active`.
- **Badge** — pill variant (cream bg, ink text) and coral variant (coral bg, white text, uppercase). Used for model names, "NEW" tags, language labels.

### Best Practices
- **Every color, spacing, and font reference goes through CSS variables** — never write `#cc785c` in a component file. Always `var(--color-primary)`.
- **Components are self-contained** — each component has its own CSS section in `components.css` (or a co-located CSS module). No global style leakage.
- **Mobile-first responsive** — write base styles for mobile, then add complexity with `min-width` media queries.
- **Semantic HTML** — use `<nav>`, `<main>`, `<aside>`, `<article>`, `<section>`. Not div soup.
- **Unique IDs on interactive elements** — every button, input, and link gets a descriptive `id` attribute for testing.

---

## 3.5 WebSocket Integration

### What To Do

1. **Create a `useChat` hook** — manages the WebSocket connection lifecycle, message state, and streaming state. Returns `{ messages, isStreaming, activeTools, sendMessage }`.

2. **Connection management**:
   - Connect when the chat page mounts
   - Reconnect automatically on disconnection (exponential backoff: 1s, 2s, 4s, max 30s)
   - Clean up on unmount
   - Show connection status indicator in the UI

3. **Message handling**:
   - On `tool_start` event: add tool to active tools list with "running" status
   - On `tool_result` event: update tool status to "done" with result
   - On `text_delta` event: append to current assistant message (streaming)
   - On `done` event: mark streaming complete, clear active tools
   - On `error` event: show error toast, stop streaming

4. **Optimistic UI** — add user message to the list immediately on send (don't wait for server confirmation). This makes the UI feel instant.

### Best Practices
- **Don't use WebSocket for everything** — session CRUD, model listing, and workspace operations use REST. WebSocket is only for chat streaming.
- **Handle stale connections** — if no message received for 60 seconds, send a ping. If no pong within 5 seconds, reconnect.
- **Debounce rapid sends** — prevent users from spamming messages while a response is streaming. Disable the send button during streaming.

---

## 3.6 REST API Client

### What To Do

1. **Create an API service module** — a thin wrapper around `fetch()` that:
   - Adds `Authorization: Bearer <token>` header automatically
   - Handles 401 responses by redirecting to login
   - Parses JSON responses
   - Throws structured errors for non-2xx responses
   - Provides methods for each API endpoint (register, login, getSessions, etc.)

2. **Store JWT in localStorage** — simple and works. For higher security, use httpOnly cookies (requires backend changes to set cookies instead of returning tokens in body).

3. **Create an `useAuth` hook** — manages auth state (token, user info, isLoggedIn). Provides login, register, logout functions. Checks token expiration on mount and redirects if expired.

### Best Practices
- **Never store tokens in component state** — use localStorage + a context/hook. Component state is lost on re-render.
- **Add request/response interceptors** — centralized error handling, logging, and token refresh logic.
- **Handle network errors gracefully** — show a toast notification, not a blank screen. "Connection lost — retrying..."

---

## 3.7 Page Structure

### Landing Page (`/`)

Build a marketing page following DESIGN.md's band rhythm pattern:

1. **Hero Band** — cream canvas. Left column: serif h1 headline ("Your AI Coding Partner" or similar), body-md subheadline describing CodeCrafter's value, coral CTA button "Start Building", secondary button "Learn More". Right column: dark product mockup card showing a CodeCrafter chat interaction.

2. **Feature Cards Band** — 3-up grid of `feature-card` components on `surface-card` background. Each card: small icon at top, `title-md` headline, `body-md` description. Features: Multi-Language Execution, Automatic Error Fix, Session Memory.

3. **Product Mockup Band** — full-width dark navy section with a large `product-mockup-card-dark` showing the actual chat interface. This is where you "show the product chrome at scale."

4. **Model Comparison Band** — cream canvas with 3 `model-comparison-card` components showing the Ollama model chain (qwen3.5, qwen3-coder, nemotron-super). Each card: model name in `display-md` serif, capability blurb, coral text link.

5. **CTA Band** — full-bleed `cta-band-coral`. Serif headline, short body text, inverted cream button.

6. **Footer** — dark navy `footer` component. 4-column layout: Product, Resources, Company, Legal. Wordmark at top. Body text in `on-dark-soft`.

### Login Page (`/login`)
- Centered card on cream canvas
- Email + password inputs using `text-input` component style
- Coral "Sign In" button
- Link to register page
- Simple, minimal — no distractions

### Register Page (`/register`)
- Same layout as login
- Email + password + confirm password
- Password strength indicator

### Chat Page (`/chat`)
- Full-height layout, no scrolling on the page itself
- Left sidebar: `SessionSidebar` (300px, dark)
- Main area: `ChatPanel` with message list + input bar
- Top: `TopNav` with model selector

### Best Practices
- **Lazy load pages** — use React.lazy() for code splitting. The landing page, auth pages, and chat page are separate chunks. Users who only visit the landing page don't download chat code.
- **SEO on landing page** — proper `<title>`, `<meta description>`, `<h1>`, Open Graph tags. The chat page doesn't need SEO.
- **Protect the chat route** — redirect to `/login` if not authenticated. Use a `ProtectedRoute` wrapper component.

---

## 3.8 Responsive Implementation

### Breakpoints (from DESIGN.md)

Follow the exact breakpoints specified in DESIGN.md:

- **Mobile (<768px)**: Hamburger nav. Hero stacks vertically (headline above mockup). Feature cards 1-up. Sidebar hidden (toggle via hamburger). Chat takes full width. Font sizes scale down (display-xl: 64→32px).

- **Tablet (768-1024px)**: Full top nav but tighter spacing. Feature cards 2-up. Sidebar 260px. Code blocks maintain font size with horizontal scroll.

- **Desktop (1024-1440px)**: Full layout. Feature cards 3-up. Sidebar 300px. Max content width 1200px centered.

- **Wide (>1440px)**: Same as desktop with more breathing room. Content width still caps at 1200px.

### Best Practices
- **Touch targets minimum 44×44px on mobile** — DESIGN.md notes some buttons are 36px (below WCAG). Increase tap area with padding on mobile.
- **Code blocks scroll, never wrap** — horizontal scroll inside dark code cards. This is explicitly stated in DESIGN.md.
- **Test on real devices** — responsive isn't just about width. Test touch interactions, virtual keyboard behavior, and scroll performance.

---

## 3.9 Build & Deploy Configuration

### What To Do

1. **Vite config** — configure dev proxy, build output directory, source map settings (enabled in dev, disabled in prod).

2. **Environment variables** — use `VITE_API_URL` and `VITE_WS_URL` for API endpoint configuration. Vite exposes `import.meta.env.VITE_*` variables. Empty defaults work with the dev proxy.

3. **Build produces static files** — `npm run build` generates `dist/` with HTML, JS, CSS, and assets. These are served by nginx in production (Phase 4).

4. **Add frontend linting** — ESLint with React plugin. Catch issues before they hit production.

---

## Phase 3 Final Checklist

- [ ] Landing page renders with correct design tokens (cream canvas, coral CTAs, serif headlines, dark mockup cards)
- [ ] Surface rhythm alternates correctly: cream → card → dark → cream → coral → dark
- [ ] Chat interface streams agent responses via WebSocket
- [ ] Tool calls display as collapsible dark cards
- [ ] Code blocks use JetBrains Mono on dark background with copy button and language badge
- [ ] Session sidebar manages sessions (create, switch, delete)
- [ ] Login/register flow works end-to-end
- [ ] Responsive at all 4 breakpoints (mobile, tablet, desktop, wide)
- [ ] No DESIGN.md violations: cream (never white), serif headlines (never sans), coral CTAs (never blue)
- [ ] All interactive elements have unique `id` attributes
- [ ] Lighthouse Performance score > 90
- [ ] `npm run build` produces optimized static bundle
