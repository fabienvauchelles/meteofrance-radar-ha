# CLAUDE.md - meteofrance-radar-ha

Home Assistant custom integration `meteofrance_radar` plus a bundled Lovelace card
(`custom:meteofrance-radar-card`) that plays the Météo-France 500 m rain radar over a fixed map
of France. Target: Home Assistant Core 2026.8.0, Python 3.14.

## Build & Run

```bash
make build      # uv sync --frozen + npm ci in card/
make check      # ruff + ruff format --check + mypy --strict + pytest, then biome, tsc, vitest, rollup
make card       # card gates and bundle rebuild only
```

## Layout

- `custom_components/meteofrance_radar/`: the integration; `www/` holds the committed card
  bundle and `basemap.png`.
- `card/`: Lit 3 + TypeScript source; rollup writes the bundle into the integration's `www/`.
- `tests/`: `core/` for pure logic, `integration/` for Home Assistant harness scenarios;
  `tests/fixtures/lame_d_eau_500_20260930T1030Z.h5` is a real product, never replace it.

## Boundaries

- Never log, print or commit an API key.
- Rebuild and commit the card bundle with every card change; CI fails on a stale bundle.
- Files under 300 lines, English on disk, no em dash.
