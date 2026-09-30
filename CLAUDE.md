# CLAUDE.md - meteofrance-radar-ha

Home Assistant custom integration `meteofrance_radar` plus a bundled Lovelace card
(`custom:meteofrance-radar-card`) that plays the Météo-France 500 m rain radar over a fixed
map of France, with a pin at the HA home. Everything runs inside HA: collect, store, render,
serve. Target: Home Assistant Core 2026.8.0, Python 3.14. User docs: `README.md`,
`docs/install.md`, `docs/data-and-storage.md`.

## Build & Run

```bash
make build      # uv sync --frozen + npm ci in card/
make check      # ruff + ruff format --check + mypy --strict + pytest, then biome, tsc, vitest, rollup
make card       # card gates and bundle rebuild only
```

Fast feedback:

```bash
.venv/bin/python -m pytest tests/core/test_tiers.py -k thinning
.venv/bin/python -m pytest tests/integration/test_views.py
cd card && npx vitest run test/timeline.test.ts
```

## Layout and layers

Inside `custom_components/meteofrance_radar/`, dependencies point inward only:

```
HA glue: __init__, config_flow, coordinator, collector, views, frontend, repairs,
         diagnostics, keyexpiry, runtime
  -> adapters: api/ (aiohttp client), decode/ (h5py, numpy projection),
               store/ (files), render/ (Pillow PNG)
     -> domain/ (pure: grid, slots, palette, tiers, periods, rate, models, ports)
```

- `domain/` imports numpy and the stdlib only. Adapters implement `domain/ports.py` and never
  import `homeassistant`. Only the glue does.
- `www/` holds the committed card bundle and `basemap.png` (1920x1080, EPSG:3857, centre
  2.5 E 46.6 N, zoom 6.4, copied from radarviz). Layers and basemap share `FRANCE_GRID`.
- `card/`: Lit 3 + TypeScript; rollup writes the bundle into `www/`.
- `tests/core/`: focused tests for pure logic (georef, tiers, codec, render).
  `tests/integration/`: HA harness scenarios (config flow, collect, retention, views,
  frontend, expiry, diagnostics). `tests/support/`: API mocks, ODIM factory, setup helper.

## Boundaries

### Always

- Run `make check` before declaring work complete; CI also fails on a stale card bundle.
- Rebuild and commit `www/meteofrance-radar-card.js` with every card change.
- Bump `RENDER_VERSION` in `domain/palette.py` when a change alters layer pixels (decode,
  reprojection, classes, PNG encoding). Layer URLs are cached a year by browsers.
- Run every blocking call (h5py, xz, numpy, Pillow, any file I/O) through
  `hass.async_add_executor_job`. One render at a time (lock in `render/service.py`).
- Write files through `store/atomic.py` (mkstemp + fsync + `os.replace`).
- Files under 300 lines, English on disk, no em dash, plain wording.

### Ask first

- Adding a runtime requirement. It needs cp314 musllinux wheels for x86_64 and aarch64, and
  must install through HA's own index (`zstandard` does not, see below).
- Changing the `/api/meteofrance_radar/frames` JSON shape or the layer URL scheme (the card
  depends on both).
- Changing the `.mfr` header or payload: stored history on users' disks must stay readable.

### Never

- Log, print, echo or commit an API key. Errors carry URL and status, never headers.
- Delete the storage root, or delete frames outside `store/`. Removing the entry keeps history.
- Replace `tests/fixtures/lame_d_eau_500_20260930T1030Z.h5`: the ±1 px georeferencing tests
  (28 radar sites) depend on this real product.
- Use `frontend.add_extra_js_url` for the card (see decisions).

## Decisions and why

- **xz, not zstd.** HA 2026.8 builds its own CPython without `_zstd`, and `zstandard` from
  PyPI loses to HA's wheel index (cp313 only). Stdlib `lzma` preset 6 on byte-shuffled uint16
  is 9 % smaller than zstd-19. The header has a `codec` field for a later switch.
- **No pyproj at runtime.** `decode/stereo.py` is an ellipsoidal polar stereographic forward
  projection in numpy; it matches pyproj to 3e-9 m and gives an identical reprojection table.
  pyproj stays a test-only reference. `h5py==3.16.0` is the only requirement; numpy and
  Pillow come with HA and are never pinned.
- **Card as a Lovelace resource.** `add_extra_js_url` injects the module before the frontend
  installs its scoped custom-element registry, so the tag never resolves. `frontend.py`
  registers static paths once per process (aiohttp refuses a route twice) and a versioned
  `module` resource in storage mode; YAML mode only logs the URL to add.
- **Keep-alive listener.** No entities means no coordinator listener, and a coordinator
  without listeners stops scheduling refreshes. Setup adds a no-op listener on purpose.
- **Plain refresh at setup,** not `async_config_entry_first_refresh`: a Météo-France outage at
  startup must not hide the history already on disk. Auth failures still start reauth.
- **Tiers** (`domain/tiers.py`): 5 min under 3 h, hourly under 30 days, 3-hourly after. Each
  bucket keeps its earliest frame; buckets nest, so thinning is idempotent and HH:05 replaces
  a missed HH:00. Frames entering the 3-hourly tier become `class_u8` (12 palette indices),
  at most 24 per maintenance run. A `class_u8` frame renders to the identical PNG.
- **Size cap** covers frames plus layers; layers get 10 % (`LAYER_CACHE_SHARE`). Oldest frames
  go first; no maximum age. Order per run: thin, downgrade, cap frames, cap layers, drop
  orphan layers.
- **Frame index in memory,** scanned once at setup, so the frames view does no disk I/O.
- **No quality filter.** QIND is not stored; the card shows every pixel.
- **Single config entry,** one key and one storage root. Default root is
  `hass.config.media_dirs["local"]/meteofrance_radar`, outside `/config` so backups stay small.

## Météo-France API facts

Checked against the live API; the Swagger is wrong or silent on each.

- Auth header `apikey: <key>`. `Authorization: Bearer` gets 401.
- Only the latest product exists. A missed slot is lost for good, so the poll runs every 60 s.
- The catalogue's `validity_time` is undocumented but present; it is the only way to skip a
  download (conditional requests always return 200). Catalogue hrefs omit `/v1`: build URLs
  from `API_BASE_URL`, never follow them.
- A transient 500 `{"code":"303001"}` "endpoint SUSPENDED" is a normal failed pass.
- Products appear about 2 min after their validity time. Quota 850 requests per 5 min.
- The key is a JWT; `exp` is read without verification. Repair 14 days ahead, reauth after.

## ODIM facts

- Slot = `/dataset1/what/enddate` + `endtime`, never `starttime`.
- `/dataset1/data1/data` uint16 3472x3472, gain 0.01 mm per 5 min, nodata 65535, undetect
  65534. `rate_mmh = acc_mm * 12`. Undetect renders as dry, nodata as grey index 11.
- Corners in `/where` are cell edges, row 0 is north. `projdef` and corners are always read
  from the file.
- In `classify`, apply the NaN mask after `np.digitize`, which maps NaN to the top class.

## Conventions

- On-screen strings are English and French (`card/src/i18n.ts`, `strings.json`,
  `translations/`). The title uses HA's time zone and locale; stored times are UTC slots
  `YYYYMMDDTHHMMZ`.
- Tests: API mocked with `aioclient_mock`, time with `freezer`, polls with
  `async_fire_time_changed`, storage under `tmp_path`. Card tests stub canvas and
  `createImageBitmap` through injected seams.
- Commits: Angular convention, `<type>(<scope>): <subject>`.
