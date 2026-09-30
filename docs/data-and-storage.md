# Data and storage

What the integration fetches from Météo-France, radar and forecasts, what it keeps, in
what form, and how much room that takes. Sizes below were measured on real products
from 30 September 2026, inside the Home Assistant 2026.8.0 image.

## The Météo-France API

The product is the 500 m "lame d'eau" mosaic of mainland France and Corsica: the rain
that fell in each 500 m cell over 5 minutes, merged from the French weather radars.

- **Base URL**: `https://public-api.meteofrance.fr/public/DPRadar/v1`. The product is
  `GET /mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500`.
- **Auth**: the key goes in an `apikey` header. The Swagger only declares OAuth2, but
  `Authorization: Bearer <key>` gets a 401.
- **Latest only.** There is no time parameter and no archive. Each image is available
  until the next one replaces it, 5 minutes later. A slot not fetched in that window
  is gone for good.
- **Delay.** An image appears about 2 minutes after the end of its 5 minutes.
- **Catalogue.** A catalogue endpoint lists the product links with a `validity_time`
  field. It is not in the Swagger, but it is there, and it is the only way to know
  whether a new image exists without downloading 2 MB: conditional requests are
  ignored and always return 200. The catalogue links leave out `/v1`, so URLs are
  always built from the base URL, never taken from the catalogue.
- **Quota**: 850 requests per 5 minutes. The integration uses about 6 (one catalogue
  call a minute, one download per new image).
- **Outages.** A 500 with `{"code":"303001"}` and "endpoint SUSPENDED" shows up now
  and then on valid URLs, usually for a minute or two. It counts as a failed pass and
  the next minute tries again.

The key is a JWT. Its `exp` claim, set when the key is generated on the portal, is read
locally (the signature is not checked) before every pass: from two weeks ahead a
repair issue offers to enter a new key, and once the key has expired the pass stops
before calling the API and Home Assistant asks for a new key (reauthentication).

**Licence.** Météo-France publishes the radar APIs on data.gouv.fr under the
Licence Ouverte / Open Licence version 2.0 (Etalab), with access through a free
account on the API portal: see the
[API Données Radar record](https://www.data.gouv.fr/dataservices/api-donnees-radar)
(licence `lov2`), the
[portal page](https://portail-api.meteofrance.fr/web/fr/api/DonneesPubliquesRadar) and
the [licence text](https://www.etalab.gouv.fr/licence-ouverte-open-licence). Reuse must
credit the source, "Météo-France"; the card does so in its title and footer.

## One collector pass

Every 60 seconds:

1. Check the key's expiry date.
2. Ask the catalogue for the current `validity_time`. Same as last time: stop here.
3. Download the product, an ODIM HDF5 file of about 2 MB.
4. Decode it in memory with `h5py`: the rain field (uint16, 3472 x 3472 cells, 0.01 mm
   per unit, `65535` for no data, `65534` for no rain detected) and its
   georeferencing. The time of an image is the end of its 5 minutes.
5. Compress it and write one file for that slot. The HDF5 file itself is never
   written to disk.
6. Tidy the storage (tiers and size cap, below).

All the decoding, compressing, rendering and file work runs in Home Assistant's
executor, off the event loop.

## History tiers

| Age | Kept | Stored as |
| --- | --- | --- |
| Under 3 hours | every 5-minute image | rain values, lossless |
| 3 hours to 30 days | one image per hour | rain values, lossless |
| Over 30 days | one image per 3 hours | the 12 display classes |

Each hour keeps its earliest image, and so does each 3-hour block. If the image at
14:00 was missed, 14:05 stands in for that hour instead of leaving it empty.

When an image passes 30 days, it is rewritten as the 12 colour classes the card
displays, instead of the raw rain values. It renders to exactly the same picture, but
takes about half the room. At most 24 images are rewritten per pass, so catching up
after a long stop does not hog the CPU. The file keeps the class limits (in mm/h) it
was made with. If a later version changes the legend, each old class is drawn in the
current class that holds its lower limit, so old history keeps its meaning.

There is no maximum age. Images are only removed when the storage goes over the size
cap, oldest first.

## File format

One file per slot, under the storage folder:

```
frames/YYYY/MM/DD/YYYYMMDDTHHMMZ.mfr    one image
layers/<style>/YYYYMMDDTHHMMZ.png       rendered cache for the card
forecast/                               latest forecasts, see "Forecasts" below
```

A `.mfr` file is a 4-byte magic `MFRF`, a format version, a JSON header (time, kind,
grid and projection read from the product, scaling), then the payload compressed with
the standard library's `lzma` (xz, preset 6). Raw rain values are byte-shuffled first
(all low bytes, then all high bytes), which takes about 10 % off. The quality index
that ships with each product is not kept: the card shows everything.

Files are written to a temporary name, flushed, then renamed into place, so a crash
never leaves a half-written image. Times are UTC throughout.

### Why xz and not zstd

Python 3.14 has zstd in its standard library, but Home Assistant builds its own Python
without the `_zstd` extension module (`import _zstd` and `import compression.zstd`
fail in the 2026.8.0 image, Python 3.14.6), and the
`zstandard` package from PyPI does not install reliably through Home Assistant's
package index. So xz it is, and it happens to be smaller:

| Codec, on the byte-shuffled field | Rainy image | Rainiest image seen | Compress | Decompress |
| --- | ---: | ---: | ---: | ---: |
| zstd level 19 (reference) | 319 KB | 367 KB | 1.6 s | 0.02 s |
| **xz preset 6 (used)** | **292 KB** | **335 KB** | 2.3 s | 0.06 to 0.09 s |
| xz preset 2 | 328 KB | 377 KB | 0.4 s | 0.06 to 0.09 s |
| zlib level 9 | 374 KB | 425 KB | 0.7 s | 0.1 s |

Timings are on x86. A Raspberry Pi 4 should be around four times slower, which is
still a few percent of one core for one image every 5 minutes. The header names its
codec, so switching to zstd later needs no change to the format.

## Measured sizes

| What | Size |
| --- | ---: |
| Product downloaded from Météo-France (HDF5, rain plus quality) | 2.05 to 2.10 MB |
| Stored image, dry France | 13 to 14 KB |
| Stored image, rain over about 5 % of the grid | 290 to 335 KB |
| Same image as 12 display classes (over 30 days old) | 130 to 150 KB |
| Rendered layer for the card (PNG, 1920 x 1080) | about 43 KB |

About half of each product is outside radar coverage, which compresses to nothing. The
size of an image is driven by how much rain there is, not by its precision: storing
8-bit values instead of 16-bit would only save about 15 %.

## The size cap

The cap (500 MB by default, 100 MB to 100 GB in the options) covers everything in the
storage folder. 10 % is set aside for rendered layers, the rest for images. After each
new image, when the images go over their share, the oldest are deleted until they fit.
The layer cache is trimmed to its share separately, least recently written first;
layers can always be rendered again.

What 500 MB holds, in the worst case where every single image is a rainy one:

- the first month (36 five-minute images and about 720 hourly ones): about 250 MB,
- then about 1.2 MB per day of 3-hourly images,
- so roughly six months in all.

Most images are much smaller than that. A dry image is 13 KB, and France is dry most
of the time, so in practice the same cap covers a lot more.

Forecasts are not part of the cap. Their folder holds two PIAF runs at most and two
small JSON files, a few megabytes in all, and is never touched by the cap.

If the disk itself runs low (under 1 GB free), new images are skipped with a warning
rather than filling it up. Those slots are lost, like any other missed image.

## Rendering

The card never sees raw data. It asks the integration for a list of frames for a
period, then for each frame's PNG layer. A layer is rendered the first time it is
asked for: the stored image is decoded, reprojected from Météo-France's polar
stereographic grid onto the Web Mercator basemap (1920 x 1080, centred on 2.5 E,
46.6 N), classed into the 12 mm/h colours, and saved as a PNG. That takes a second or
two. One render runs at a time; cached layers are served straight away. The
reprojection table (about 19 MB) is built once and kept in memory; at most two are
kept, for the unlikely case of a history spanning a change of the Météo-France grid.

The rain rate shown is the 5-minute amount times 12, in mm/h. The legend classes start
at 0.1 mm/h and go up to 70 mm/h. Cells with no data are drawn in a faint grey, so a
radar outage does not look like dry weather.

Layer URLs carry a style id that changes whenever the colours, the grid or the
renderer change, so browsers can cache a layer for a year without ever showing a stale
one.

## Forecasts

Forecasts come from three Météo-France APIs besides DPRadar, each optional (see
[`install.md`](install.md) for the subscriptions). All three are WCS 2.0.1 services on
the same portal, with the same `apikey` header. One request fetches one time step, as
a GRIB2 file.

| API | Runs | Used for | What is fetched |
| --- | --- | --- | --- |
| PIAF (`PrevisionImmediatePrecipitations`) | every 5 min, ready about 9 min later | radar card after "now", rain bar 0 to +3 h | 20 steps of the whole of France, one run in three |
| AROME-PI | every hour, ready 20 to 50 min later | rain bar +3 h to +6 h | the cells around the home, 24 steps of 15 min |
| AROME | every 3 hours, steps published over time | rain bar after +6 h, up to midnight | the cells around the home, hourly |

### PIAF maps

Every minute the integration checks whether the next PIAF run it wants is out, with
one small DescribeCoverage request (it answers 404 until the run is published). It
takes one run every 15 minutes, at :00, :15, :30 and :45, and fetches 20 steps: every
5 minutes from +5 to +60 min, then every 15 minutes up to +180 min. PIAF gives rain in
mm per 5 minutes, times 12 for mm/h, like the radar.

Each step is a 3.5 MB GRIB2 file on a 0.01 degree latitude and longitude grid. It is
decoded in memory with numpy, reprojected onto the same Web Mercator map as the radar,
classed with the same colours, and saved as a PNG layer. The GRIB2 file is never
written to disk. The value at the home location is kept for the rain bar. A missed run
is skipped, never fetched late.

### Pin series for the rain bar

AROME-PI and AROME are only needed at the home location, so each request asks for a
0.03 degree box around it, a 3 by 3 GRIB2 file of about 200 bytes, and keeps the
centre cell. AROME-PI (a rain rate in mm/h) is fetched once per new hourly run.
AROME (an hourly amount, so also mm/h) is checked every hour, and only the steps not
fetched yet are requested. When the home location moves, the latest run is fetched
again for the new place.

### Request budgets

Météo-France allows 100 requests per minute per forecast API. The integration keeps
each API under 90 a minute, with at least 0.7 s between two requests.

| API | Requests per hour | Burst | Download |
| --- | --- | --- | --- |
| PIAF | about 90 (4 runs of 20 steps, plus the checks) | 20 in about 25 s | about 280 MB per hour |
| AROME-PI | 24, plus up to 36 checks (usually about 10) | 24 | under 10 KB per hour |
| AROME | 2 or 3, up to 24 on a new run | 24 | under 10 KB per hour |

Each PIAF step takes well under a second of one core to decode and render, one at a
time, sharing the radar's render lock. The reprojection table for the forecast grid
(about 18 MB) is built once and kept in memory.

### When a forecast API fails

A 401 or 403 means the key is not subscribed to that API: a repair names the API to
subscribe to, and it is tried again every hour. Any other failure is retried after 2,
4, 8, 16, then every 30 minutes. A GRIB2 file in a form the decoder does not read (a
packing other than simple packing, or a bitmap of missing cells) is refused loudly
and counts as a failure. The radar never waits for a forecast, and error messages
name the API, the request and the status, never the query (which holds the home
location) nor the key.

### Forecast storage

```
forecast/piaf/<RUN>/<VALID>.png          one layer per step
forecast/piaf/<RUN>/run.json             run, style, steps, and the value at the home
forecast/piaf/.staging-<RUN>/            run being fetched, moved into place when complete
forecast/pins/aromepi.json               latest AROME-PI values at the home
forecast/pins/arome.json                 latest AROME values at the home
```

`RUN` and `VALID` are UTC times, `YYYYMMDDTHHMMZ`. Only the latest PIAF run is listed
to the card. The one before it stays on disk until the next run lands, so a card that
fetched the list just before a new run still gets its images. Older runs, runs of an
older style and unfinished staging folders are deleted. Nothing is archived.

## HTTP endpoints

All require a logged-in Home Assistant user, like the rest of the API.

- `GET /api/meteofrance_radar/frames?period=3h|24h|7d|30d|all`: the frames of the
  period, the basemap URL, the grid, the pin position of the home location, the legend,
  the attribution and, for each frame, how many minutes were skipped before it. A
  `forecast` part lists the PIAF frames after "now": the status of PIAF, its run, the
  "now" time (the latest radar image, or the current 5 minutes when that image is more
  than 15 minutes old), and for each frame its time, its lead in minutes and its URL.
  The list is empty when there is no forecast.
- `GET /api/meteofrance_radar/forecast/<style>/<RUN>/<VALID>.png`: one forecast layer,
  cached a year by the browser. Only the current and the previous run answer; anything
  else is 404.
- `GET /api/meteofrance_radar/pin_series`: the rain bar. The time window (3 hours ago
  to midnight in Paris, at least 6 hours ahead), whether a home location is set, the
  legend, and the segments in order, each with its source (`radar`, `piaf`,
  `aromepi`, `arome`), start, end, rate in mm/h (`null` for no data) and colour class.
  Each source takes over where the previous one ends, so when PIAF is missing,
  AROME-PI starts at "now". A `sources` part gives the status and run of each one.
- `GET /api/meteofrance_radar/layers/<style>/<YYYYMMDDTHHMMZ>.png`: one rendered layer.
  A layer that cannot be rendered answers 500 with `{"error": "cannot render layer",
  "slot": ...}` and nothing more; the details go to the Home Assistant log, in full
  the first time for a slot and at debug level after that.

The card bundle and the basemap are served as static files under `/meteofrance_radar/`.
