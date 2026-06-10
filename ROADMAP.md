# 🗺️ AETHER Product Roadmap

> Generated: 2026-06-10
> Current state: Sprint AETHER-MQTT-1 complete (6 dashboard pages, 19 API routes, MQTT integration, all 24 params wired)

---

## Current State (Shipped)

```
✅ Core simulation engine          ✅ 3 agents (Solara/Veridian/Hal-90)
✅ Orchestrator + quality gates     ✅ 24 env config params wired
✅ Multi-page dashboard (6 pages)   ✅ MQTT console + publish integration
✅ Settings / Scenarios / Agents    ✅ History browser with JSON export
✅ 19 API routes                    ✅ 4/4 tests + 5/5 quality gates
```

---

## Phase I: Core Hardening *(~21h — high impact, low effort)*

| # | Feature | Effort | Why now |
|---|---------|--------|---------|
| 1 | **Simulation comparison** — side-by-side diff of two history entries | ~4h | Users need to compare "what changed" between runs |
| 2 | **Scenario presets** — save/load named scenarios to disk as JSON | ~3h | Scenarios page currently has no persistence |
| 3 | **Real-time charting** — replace static bar charts with SVG sparklines/mini-charts for battery/O2/power over 24 cycles | ~6h | Telemetry is the most visually impressive part; bars don't do it justice |
| 4 | **Phase colour-coding** — color the pipeline status phase by type (green=energy, gold=biological, cyan=mediation, white=nominal) | ~1h | Instant visual scan of where the pipeline is |
| 5 | **Dashboard live mode** — during simulation, show per-cycle updates in real time (not just after completion) | ~4h | The "running" state is currently a blank loading screen |
| 6 | **Anomaly timeline** — visual bar showing which cycles had which anomaly types, colour-coded | ~3h | Makes anomaly patterns visible at a glance |

---

## Phase II: Advanced Simulation *(~33h — moderate effort, high engagement)*

| # | Feature | Effort | Why now |
|---|---------|--------|---------|
| 7 | **Multi-run orchestration** — run 10+ simulations in parallel with different configs, compare aggregate metrics | ~8h | Turns it into a proper analysis tool |
| 8 | **Parameter sweep** — run N simulations varying one parameter (e.g., `array_efficiency` from 5-25%) and plot results | ~6h | Discover optimal configurations |
| 9 | **Custom anomaly scripts** — write Python snippets that inject complex multi-cycle anomaly sequences | ~5h | Scenarios become programmable |
| 10 | **Simulation replay** — scrub through a completed run cycle-by-cycle watching state change | ~6h | Best way to understand agent behaviour |
| 11 | **Agent decision trace** — expandable log showing exactly why each agent made each decision (with data) | ~4h | Debugging agent conflicts |
| 12 | **Hal-90 mediation visualizer** — graph showing Solara threshold vs Veridian request, and where Hal-90 landed | ~4h | The core conflict becomes visible |

---

## Phase III: Data & Persistence *(~23h — foundational, unlocks everything else)*

| # | Feature | Effort | Why now |
|---|---------|--------|---------|
| 13 | **SQLite persistence** — replace in-memory `simulation_history` with SQLite; history survives restarts | ~6h | **Foundational** — unlocks every feature below |
| 14 | **User authentication** — simple token-based auth for dashboard access (no multi-user yet) | ~4h | Needed before any deployment |
| 15 | **CSV export** — download telemetry/summary as CSV (in addition to JSON) | ~2h | User requested in history page |
| 16 | **PDF report generation** — one-click PDF with charts, summary, agent stats | ~6h | Professional output for stakeholders |
| 17 | **Session notes** — attach text notes to any simulation run | ~2h | Remember why you ran that config |
| 18 | **Configuration versioning** — every run snapshots the full config; you can restore any past config with one click | ~3h | "That run was good — let me repeat it" |

---

## Phase IV: Real-Time & Communication *(~22h — the "wow" layer)*

| # | Feature | Effort | Why now |
|---|---------|--------|---------|
| 19 | **WebSocket streaming** — replace 3s HTTP polling with real-time SSE/WebSocket for live status updates | ~6h | Smooth real-time feel |
| 20 | **MQTT broker health** — auto-reconnect, broker uptime monitoring, topic traffic graphs | ~4h | MQTT console becomes operational |
| 21 | **Email alerts** — configure email/webhook notifications on anomaly/emergency events | ~4h | Useful for unattended simulation monitoring |
| 22 | **Agent live logs** — stream agent stdout/stderr to a collapsible log panel in the dashboard | ~3h | Debugging without terminal access |
| 23 | **Multi-client sync** — multiple browser tabs see the same state (via MQTT/WebSocket bridge) | ~5h | Team visibility |

---

## Phase V: AI & Intelligence *(~32h — the differentiator)*

| # | Feature | Effort | Why now |
|---|---------|--------|---------|
| 24 | **Ollama integration** — replace deterministic agent logic with local LLM calls (Haiku/Mistral) for natural-language decisions | ~8h | Agents become truly autonomous |
| 25 | **Anomaly prediction** — train a simple ML model on past runs to predict anomaly probability per cycle | ~6h | Proactive vs reactive |
| 26 | **Natural-language post-mortem** — "Explain why the battery died on cycle 14" generates an LLM summary | ~4h | Makes simulation output understandable |
| 27 | **Autonomous optimization** — let the AI tweak parameters and re-run to find optimal habitat config automatically | ~8h | The "set and forget" dream |
| 28 | **Agent personality profiles** — define agent behaviour through natural-language prompts instead of hardcoded thresholds | ~6h | "Make Solara more aggressive about conservation" |

---

## Phase VI: Polish & Production *(~27h — ship-ready)*

| # | Feature | Effort | Why now |
|---|---------|--------|---------|
| 29 | **Responsive mobile layout** — sidebar collapses, cards stack, touch-friendly sliders | ~6h | Phone access |
| 30 | **PWA support** — manifest, service worker, offline fallback page | ~3h | Installable on desktop/mobile |
| 31 | **Dark/amber theme toggle** — optional warm amber theme (in addition to green emerald) | ~2h | User preference |
| 32 | **Keyboard shortcuts** — `R` to run, `S` settings, `1-6` nav | ~2h | Power-user speed |
| 33 | **Deployment** — Dockerfile + docker-compose with Mosquitto, SQLite, dashboard | ~4h | One-command deploy |
| 34 | **Gumroad license delivery** — automated license key generation and verification | ~6h | Revenue enablement |
| 35 | **Landing page polish** — final copy, OG images, testimonials block | ~4h | First impression |

---

## Summary

| Phase | Hours | Value | Dependency |
|-------|-------|-------|------------|
| **I: Core Hardening** | ~21h | ★★★★★ Fixes paper cuts, immediate UX improvement | None |
| **II: Advanced Simulation** | ~33h | ★★★★☆ Turns demo into platform | None |
| **III: Data & Persistence** | ~23h | ★★★★★ Must-have for deployment | None |
| **IV: Real-Time** | ~22h | ★★★☆☆ Wow factor, relies on III | SQLite (Phase III) |
| **V: AI & Intelligence** | ~32h | ★★★★★ The differentiator | Ollama running on host |
| **VI: Polish & Production** | ~27h | ★★★★☆ Ship-ready | All of the above |

**Total remaining: ~158 hours** (~4 weeks full-time)

---

## Recommended Path

**Immediate (Phase I):** 6 quick wins that make the biggest visual/UX difference. Charting and live mode transform how the dashboard *feels*.

**Then pick one:**
- **Revenue path** → skip to Phase VI (#34 Gumroad), ship a license-gated beta
- **Depth path** → Phase II + III, build the complete simulation platform
- **AI path** → Phase V, make it intelligent with Ollama
