# meteofrance-radar-ha

The Météo-France rain radar in Home Assistant: a Lovelace card that plays the 500 m
rain mosaic over a map of France, with a pin on your home, and keeps weeks of history
on your own disk.

This is an unofficial community project. It is not affiliated with, endorsed by, or
supported by Météo-France.

## What you get

One integration and one card. Add your Météo-France API key, put the card on a
dashboard, and that is it.

- **An animated radar card.** Play, pause, step one frame back or forward, scrub the
  time slider, and pick a period: 3 h, 24 h, 7 days, 30 days, or everything stored.
  A pin marks the home location set in Home Assistant.
- **The 500 m "lame d'eau" mosaic.** Mainland France and Corsica, one image every
  5 minutes, shown as rain rate in mm/h with a legend.
- **History kept at home.** Every 5-minute image for the last 3 hours, one per hour
  up to a month, one every 3 hours beyond that, until the size cap is reached. By
  default the cap is 500 MB, which covers several months.
- **Gaps are shown, not hidden.** When an image is missing the card jumps over it
  and says so in the title ("gap of 25 min skipped").
- **English and French**, following the language and time zone set in Home
  Assistant.

There are no entities. No sensor, no camera, no binary sensor: only the card.

## Why this exists

The radar maps on weather sites are fine for a quick look, but they show the next
hour or the last one, never last Tuesday's storm, and never on your own dashboard.
Météo-France publishes the radar mosaic through a free public API, but only the
latest image: no archive, no time parameter. So the history has to be collected as
it comes, every 5 minutes, and stored somewhere. This integration does that inside
Home Assistant, with no add-on and no extra server, and renders the images for the
card on demand.

## Install

Full steps, with what each screen looks like, are in
[`docs/install.md`](docs/install.md).

1. **Get an API key.** Create a free account on
   [portail-api.meteofrance.fr](https://portail-api.meteofrance.fr), subscribe to
   the **DPRadar** API, and generate an API key. Keep the key at hand; it is valid
   for about a year.
2. **HACS.** HACS > top-right menu > Custom repositories, add
   `https://github.com/fabienvauchelles/meteofrance-radar-ha` as an
   **Integration**, then download **Météo-France Radar**.
3. **Restart Home Assistant Core.** A new integration is not loaded by a config
   reload. On first start Home Assistant installs `h5py`, which takes a minute.
4. **Add the integration.** Settings > Devices & Services > Add integration >
   **Météo-France Radar**, then paste the key. It is checked against the API
   before the entry is saved.
5. **Add the card.** Open a dashboard, Edit > Add card, search for
   **Météo-France Radar**. If it is not in the list, reload the browser tab once.
   The first image shows up a few minutes after step 4.

## Constraints worth knowing before you start

None of these are bugs. They come from how the Météo-France API works.

- **A missed image is lost for good.** The API only ever serves the latest
  image. If Home Assistant is stopped, restarting, or offline when an image is
  published, that 5-minute slot never comes back. The integration checks every
  minute to keep this rare, and the card marks the gaps.
- **History starts the day you install.** There is no backfill. The 30-day view
  fills up over 30 days.
- **France only.** The mosaic covers mainland France and Corsica. If your home is
  outside the map, the pin is not drawn; the radar still plays.
- **The API key expires.** Keys are generated with a one-year lifetime. Two weeks
  before the date, a repair shows up in Settings > System > Repairs; follow it to
  paste a new key. Once the key has expired, Home Assistant asks for a new one and
  collection stops until you give it. The stored history is kept either way.
- **Météo-France has hiccups.** The API sometimes answers "endpoint SUSPENDED"
  for a minute or two. That pass is logged as failed and the next one usually
  works. If it lasts longer than 5 minutes, images are missed.
- **The map is fixed.** One view of France at a fixed zoom, the same for everyone.
  No panning, no zooming in on your town.
- **Every pixel is shown.** There is no quality filter: what the radar sees,
  including the odd ground clutter or ghost echo, is drawn.
- **YAML dashboards need one manual step.** If your Lovelace resources are in
  YAML, add `/meteofrance_radar/meteofrance-radar-card.js` as a `module` resource
  yourself. Dashboards managed from the UI get it automatically.

## Configuration

The API key is set when the integration is added, and changed later from its
menu (Reconfigure). The rest lives in the integration's options.

| Option | Default | Meaning |
| --- | --- | --- |
| Storage folder | `/media/meteofrance_radar` | Absolute path where the images are stored. Kept outside `/config` so backups stay small. Changing it does not move what is already stored. |
| Size cap | `500` MB | From 100 to 100,000 MB. Above it, the oldest images are removed first. 10 % of it is set aside for the rendered image cache. |

Changing the key, reauthenticating, removing the integration or reinstalling it
never deletes the stored history.

The card options are all optional, and can be set in the card's visual editor or
in YAML.

| Card option | Default | Meaning |
| --- | --- | --- |
| `default_period` | `3h` | Period shown when the card opens: `3h`, `24h`, `7d`, `30d` or `all`. |
| `autoplay` | `true` | Start playing as soon as the card is shown. |
| `show_legend` | `true` | Show the mm/h legend under the map. |
| `frame_duration_ms` | `500` | Time spent on each image, from 100 to 5000 ms. |
| `crossfade_ms` | `300` | Fade between two images, from 0 to 2000 ms. Never longer than `frame_duration_ms`. No fade across a gap. |

```yaml
type: custom:meteofrance-radar-card
default_period: 24h
autoplay: true
frame_duration_ms: 400
```

## Status and limitations

Version `0.1.0`. First release, written against Home Assistant 2026.8.

- **Tested on x86_64.** `h5py` was installed and run with Home Assistant's own
  installer in the 2026.8.0 image. An `aarch64` wheel exists on PyPI but has not
  been tried on a Raspberry Pi yet.
- **CPU cost.** Each new image costs about 2.5 s of one core on x86 to decode and
  compress, and each image the card asks for the first time about 1 to 2 s to
  render. A Raspberry Pi 4 is several times slower; it still works, but opening the
  30-day view on a cold cache takes a while.
- **Compression is xz, not zstd.** Home Assistant's Python is built without the
  `zstd` module, so frames are stored with the standard library's `lzma`, which
  turned out slightly smaller anyway. Details and measured sizes are in
  [`docs/data-and-storage.md`](docs/data-and-storage.md).
- **One config entry.** One key, one storage folder.

## Development

Two areas, each with its own tools: the integration (`.venv`, provisioned by uv on
Python 3.14) and the card (`card/`, npm).

```
make build       # uv sync --frozen, then npm ci in card/
make check       # ruff, ruff format, mypy --strict, pytest, then biome, tsc, vitest, rollup
make lint        # ruff only
make typecheck   # mypy --strict only
make test        # pytest only
make card        # card gates, then rebuild the committed bundle
```

The integration follows a strict inward dependency rule: `domain/` is pure (numpy
and the standard library), the adapters (`api/`, `decode/`, `store/`, `render/`)
implement the protocols in `domain/ports.py`, and only the top-level modules import
Home Assistant. The polar stereographic projection is a few lines of numpy, checked
against `pyproj` in the tests only, so `h5py` is the one runtime requirement.

Tests are full scenarios through Home Assistant's test harness (config flow, setup,
collector passes against a mocked API, the HTTP views), plus focused tests for the
georeferencing, tiers and the frame format. The georeferencing tests run on a real
Météo-France product in `tests/fixtures/` and check that 28 radar sites land within
one pixel of where they belong.

The card bundle is built by rollup into
`custom_components/meteofrance_radar/www/` and committed, because HACS installs
from the repository. CI rebuilds it and fails if the committed file is stale.

## License

`LicenseRef-FSL-1.1-MIT`, the Functional Source License 1.1 with an MIT future
license. See [`LICENSE`](LICENSE).

## Trademarks and data credit

Météo-France is a trademark of Météo-France. It is used here only to say where the
data comes from. The icons under `custom_components/meteofrance_radar/brand/` are
drawn for this project and do not use any Météo-France logo.

- **Radar data: Météo-France.** The "lame d'eau" mosaic comes from the DPRadar API
  on the [Météo-France API portal](https://portail-api.meteofrance.fr), published
  as open data under the Etalab Open Licence 2.0. The card credits Météo-France in
  its title and footer. Your use of the API is also bound by the portal's terms.
- **Departments:** IGN ADMIN EXPRESS COG 2018, simplified by
  [france-geojson](https://github.com/gregoiredavid/france-geojson), Etalab Open
  Licence.
- **Coastlines and borders outside France:**
  [Natural Earth](https://www.naturalearthdata.com), public domain.
