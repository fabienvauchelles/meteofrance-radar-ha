# Météo-France Radar for Home Assistant

Unofficial integration and Lovelace card that play the Météo-France rain radar (500 m "lame
d'eau" mosaic, mainland France) over a map of France, with a pin at your Home Assistant home.
Radar data: Météo-France. This project is not affiliated with Météo-France.

Work in progress: the full documentation lands with the first release.

## Development

```bash
make build   # uv sync (Python 3.14, Home Assistant 2026.8) and npm ci for the card
make check   # ruff, mypy --strict, pytest, biome, tsc, vitest, rollup build
```

## Licence

FSL-1.1-MIT, see [LICENSE](LICENSE).
