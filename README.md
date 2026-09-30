# meteofrance-radar-ha

The Météo-France rain radar in Home Assistant: a Lovelace card that plays the 500 m
rain mosaic over a map of France, with a pin on your home, carries on into the next
3 hours with the Météo-France nowcast, and keeps weeks of history on your own disk. A
second card shows the rain at home as a single bar, from 3 hours ago to tonight.

This is an unofficial community project. It is not affiliated with, endorsed by, or
supported by Météo-France.

## What you get

One integration and two cards. Add your Météo-France API key, put a card on a
dashboard, and that is it.

- **An animated radar card.** Play, pause, step one frame back or forward, scrub the
  time slider, and pick a period: 3 h, 24 h, 7 days, 30 days, or everything stored.
  A pin marks the home location set in Home Assistant.
- **The 500 m "lame d'eau" mosaic.** Mainland France and Corsica, one image every
  5 minutes, shown as rain rate in mm/h with a legend.
- **History kept at home.** Every 5-minute image for the last 3 hours, one per hour
  up to a month, one every 3 hours beyond that, until the size cap is reached. By
  default the cap is 500 MB, which covers several months.
- **The next 3 hours.** After the last radar image the animation goes on with the
  PIAF nowcast: every 5 minutes for the first hour, then every 15 minutes. Forecast
  images are marked: "Forecast +45 min" in the title, a "Forecast" banner on the map,
  and a "now" marker on the time slider. Forecasts need extra (free) subscriptions on
  the Météo-France portal, see below; without them the card simply stops at "now".
- **A rain bar card.** One horizontal bar with the rain at your home, from 3 hours ago
  to midnight (and at least 6 hours ahead): the radar history for the past, then the
  PIAF, AROME-PI and AROME forecasts. Same colours as the radar legend, a "now" line,
  the forecast part lightly hatched, and the time and rate when you hover a segment.
- **Gaps are shown, not hidden.** When an image is missing the card jumps over it
  and says so in the title ("gap of 25 min skipped").
- **English and French**, following the language and time zone set in Home
  Assistant.

There are no entities. No sensor, no camera, no binary sensor: only the cards.

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
   for about a year. For forecasts, also subscribe to the three APIs listed in
   [Forecasts](#forecasts) before generating the key.
2. **HACS.** HACS > top-right menu > Custom repositories, add
   `https://github.com/fabienvauchelles/meteofrance-radar-ha` as an
   **Integration**, then download **Météo-France Radar**.
3. **Restart Home Assistant Core.** A new integration is not loaded by a config
   reload. On first start Home Assistant installs `h5py`, which takes a minute.
4. **Add the integration.** Settings > Devices & Services > Add integration >
   **Météo-France Radar**, then paste the key. It is checked against the API
   before the entry is saved.
5. **Add the cards.** Open a dashboard, Edit > Add card, search for
   **Météo-France Radar** or **Météo-France Rain Bar**. If they are not in the list,
   reload the browser tab once. The first image shows up a few minutes after step 4.

## Forecasts

The radar comes from the DPRadar API. Forecasts come from three more APIs on the same
portal, all free and all optional. Each one you skip only removes its part:

| Portal API | Used for |
| --- | --- |
| **PrevisionImmediatePrecipitations**, "Modèle AROME Prévision Immédiate Agrégée Fusionnée (PIAF)" | The forecast images on the radar card, and the next 3 hours of the rain bar. |
| **AROME-PI**, "Modèle AROME Prévision Immédiate" | The rain bar from +3 h to +6 h. |
| **AROME**, "Modèle AROME" | The rain bar after +6 h, up to midnight. |

A key only carries the subscriptions that existed when it was generated. So after
subscribing, **generate a new key** on the portal, then in Home Assistant open
Settings > Devices & Services > Météo-France Radar > three-dot menu > **Reconfigure**
and paste it. The radar history is kept.

When the key is not subscribed to one of them, the radar goes on as usual, and
Settings > System > Repairs shows which API to subscribe to. The repair goes away by
itself once that API answers.

**Bandwidth.** The PIAF images are downloaded for the whole of France, 20 of them per
forecast run, one run every 15 minutes: about **280 MB per hour**, 6.7 GB a day. They
are turned into small images for the card and not kept. The AROME-PI and AROME
requests only ask for the few cells around your home, a few kilobytes an hour. On a
metered connection, leave the PIAF subscription out.

## Constraints worth knowing before you start

None of these are bugs. They come from how the Météo-France API works.

- **A missed image is lost for good.** The API only ever serves the latest
  image. If Home Assistant is stopped, restarting, or offline when an image is
  published, that 5-minute slot never comes back. The integration checks every
  minute to keep this rare, and the card marks the gaps.
- **History starts the day you install.** There is no backfill. The 30-day view
  fills up over 30 days.
- **France only.** The mosaic covers mainland France and Corsica. If your home is
  outside the map, the pin is not drawn; the radar still plays. The rain bar needs a
  home location in France.
- **Forecasts are not archived.** Only the latest forecast run is kept. Once a time
  has passed, the card shows what the radar saw, not what was forecast.
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
in YAML. The editor shows the defaults when an option is not set.

### Radar card

| Card option | Default | Meaning |
| --- | --- | --- |
| `default_period` | `3h` | Period shown when the card opens: `3h`, `24h`, `7d`, `30d` or `all`. |
| `autoplay` | `true` | Start playing as soon as the card is shown. |
| `show_legend` | `true` | Show the mm/h legend under the map. |
| `frame_duration_ms` | `500` | Time spent on each image, from 100 to 5000 ms. |
| `crossfade_ms` | `300` | Fade between two images, from 0 to 2000 ms. Never longer than `frame_duration_ms`. No fade across a gap. |
| `show_forecast` | `true` | Play the PIAF forecast after the last radar image. |

```yaml
type: custom:meteofrance-radar-card
default_period: 24h
autoplay: true
frame_duration_ms: 400
```

### Rain bar card

| Card option | Default | Meaning |
| --- | --- | --- |
| `title` | none | Text shown above the bar. |
| `show_legend` | `false` | Show the mm/h legend under the bar. |

```yaml
type: custom:meteofrance-rain-bar-card
title: Rain at home
show_legend: true
```

The bar refreshes every 5 minutes. Its hour labels follow the time zone and language
set in Home Assistant.

### Sections view sizing

Both cards support the `grid_options` of a sections view. The radar card takes the
full width by default and fits a half-width column (6 of 12 columns): the map scales
to the card width at 16:9 and the controls wrap. With a fixed number of `rows`, the
map fits the height and stays centred. The rain bar needs one row and can go down to
a quarter of the width.

```yaml
type: custom:meteofrance-radar-card
grid_options:
  columns: 6
```

## Status and limitations

Version `0.2.1`, written against Home Assistant 2026.8 and running on 2026.9.

- **Tested on x86_64.** `h5py` was installed and run with Home Assistant's own
  installer in the 2026.8.0 image. An `aarch64` wheel exists on PyPI but has not
  been tried on a Raspberry Pi yet.
- **CPU cost.** Each new image costs about 2.5 s of one core on x86 to decode and
  compress, and each image the card asks for the first time about 1 to 2 s to
  render. A Raspberry Pi 4 is several times slower; it still works, but opening the
  30-day view on a cold cache takes a while.
- **Compression is xz, not zstd.** Home Assistant's Python is built without the
  `_zstd` module, so frames are stored with the standard library's `lzma`, which
  turned out slightly smaller anyway. Details and measured sizes are in
  [`docs/data-and-storage.md`](docs/data-and-storage.md).
- **One config entry.** One key, one storage folder.
- **Forecast CPU cost.** Each PIAF image costs well under a second to decode and
  render, 20 per run, one at a time and never alongside a radar render.

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
against `pyproj` in the tests only, so `h5py` is the one runtime requirement. The
forecast GRIB2 files are read by a small numpy decoder too, with no eccodes.

Tests are full scenarios through Home Assistant's test harness (config flow, setup,
collector passes and forecast runs against a mocked API, the HTTP views), plus
focused tests for the georeferencing, tiers, the frame format and the GRIB decoder.
The georeferencing tests run on a real Météo-France product in `tests/fixtures/` and
check that 28 radar sites land within one pixel of where they belong.

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

- **Forecast data: Météo-France.** PIAF, AROME-PI and AROME come from the same
  portal and are bound by its terms; the cards credit Météo-France.
- **Radar data: Météo-France.** The "lame d'eau" mosaic comes from the DPRadar API
  on the [Météo-France API portal](https://portail-api.meteofrance.fr/web/fr/api/DonneesPubliquesRadar),
  open data under the Licence Ouverte / Open Licence version 2.0 (Etalab), reached with
  a free portal account (source:
  [data.gouv.fr record of the API](https://www.data.gouv.fr/dataservices/api-donnees-radar)).
  The licence asks you to credit the source; the card credits Météo-France in its
  title and footer. Your use of the API is also bound by the portal's terms.
- **Departments:** IGN ADMIN EXPRESS COG 2018, simplified by
  [france-geojson](https://github.com/gregoiredavid/france-geojson), Etalab Open
  Licence.
- **Coastlines and borders outside France:**
  [Natural Earth](https://www.naturalearthdata.com), public domain.
