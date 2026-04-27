# Wave D2 Themed Mockups - Master Index

Four maximally-different visual themes applied to the 5 Wave D2 dashboard mockups.
Originals live in `research/mockups/*.html` (Bloomberg-terminal aesthetic).
Themed variants live in `research/mockups/themed/<theme-slug>/`.

## Themes

| Slug | Name | Palette | Mood | Showcase |
|------|------|---------|------|----------|
| `botanical-garden` | Botanical Garden | `#f5f3ed` / `#1f2418` / `#4a7c59` / `#f9a620` / `#b7472a` | Editorial · Cream + Fern + Marigold + Terracotta | [`botanical-garden/INDEX.html`](botanical-garden/INDEX.html) |
| `modern-minimalist` | Modern Minimalist | `#ffffff` / `#000000` / `#000000` / `#36454f` / `#000000` | Brutalist · Pure white + black + slate | [`modern-minimalist/INDEX.html`](modern-minimalist/INDEX.html) |
| `midnight-galaxy` | Midnight Galaxy | `#15082b` / `#e6e6fa` / `#a490c2` / `#ff79c6` / `#4a4e8f` | Synthwave · Deep purple + cosmic blue + lavender | [`midnight-galaxy/INDEX.html`](midnight-galaxy/INDEX.html) |
| `golden-hour` | Golden Hour | `#ebe0c8` / `#4a403a` / `#c1666b` / `#f4a900` / `#6b4f7a` | Lab Notebook · Warm beige + chocolate + mustard + terracotta | [`golden-hour/INDEX.html`](golden-hour/INDEX.html) |

## Mockups (each rendered in 4 themes)

- **cost-router-status**
  - [`botanical-garden/cost-router-status.html`](botanical-garden/cost-router-status.html)
  - [`modern-minimalist/cost-router-status.html`](modern-minimalist/cost-router-status.html)
  - [`midnight-galaxy/cost-router-status.html`](midnight-galaxy/cost-router-status.html)
  - [`golden-hour/cost-router-status.html`](golden-hour/cost-router-status.html)
- **journey-tracker-12d**
  - [`botanical-garden/journey-tracker-12d.html`](botanical-garden/journey-tracker-12d.html)
  - [`modern-minimalist/journey-tracker-12d.html`](modern-minimalist/journey-tracker-12d.html)
  - [`midnight-galaxy/journey-tracker-12d.html`](midnight-galaxy/journey-tracker-12d.html)
  - [`golden-hour/journey-tracker-12d.html`](golden-hour/journey-tracker-12d.html)
- **swarm-topology**
  - [`botanical-garden/swarm-topology.html`](botanical-garden/swarm-topology.html)
  - [`modern-minimalist/swarm-topology.html`](modern-minimalist/swarm-topology.html)
  - [`midnight-galaxy/swarm-topology.html`](midnight-galaxy/swarm-topology.html)
  - [`golden-hour/swarm-topology.html`](golden-hour/swarm-topology.html)
- **flume-latent-explorer**
  - [`botanical-garden/flume-latent-explorer.html`](botanical-garden/flume-latent-explorer.html)
  - [`modern-minimalist/flume-latent-explorer.html`](modern-minimalist/flume-latent-explorer.html)
  - [`midnight-galaxy/flume-latent-explorer.html`](midnight-galaxy/flume-latent-explorer.html)
  - [`golden-hour/flume-latent-explorer.html`](golden-hour/flume-latent-explorer.html)
- **compound-loop-traces**
  - [`botanical-garden/compound-loop-traces.html`](botanical-garden/compound-loop-traces.html)
  - [`modern-minimalist/compound-loop-traces.html`](modern-minimalist/compound-loop-traces.html)
  - [`midnight-galaxy/compound-loop-traces.html`](midnight-galaxy/compound-loop-traces.html)
  - [`golden-hour/compound-loop-traces.html`](golden-hour/compound-loop-traces.html)

## File map

```
research/mockups/themed/
  botanical-garden/
    cost-router-status.html
    journey-tracker-12d.html
    swarm-topology.html
    flume-latent-explorer.html
    compound-loop-traces.html
    THEME.md
    INDEX.html
  modern-minimalist/
    cost-router-status.html
    journey-tracker-12d.html
    swarm-topology.html
    flume-latent-explorer.html
    compound-loop-traces.html
    THEME.md
    INDEX.html
  midnight-galaxy/
    cost-router-status.html
    journey-tracker-12d.html
    swarm-topology.html
    flume-latent-explorer.html
    compound-loop-traces.html
    THEME.md
    INDEX.html
  golden-hour/
    cost-router-status.html
    journey-tracker-12d.html
    swarm-topology.html
    flume-latent-explorer.html
    compound-loop-traces.html
    THEME.md
    INDEX.html
  INDEX.md
```

## Methodology

Token substitution: original `:root` CSS variable block was rewritten per-theme; Google Fonts link + body/display/mono `font-family` declarations were swapped; light themes received an override block disabling the scanline overlay, vignette, and box-shadow glows that only make sense on a near-black ground.

All mockups remain valid standalone HTML and render with internet access (CDNs: Tailwind, React, Recharts, Google Fonts).
