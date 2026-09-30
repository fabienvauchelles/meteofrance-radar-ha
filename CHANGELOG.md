# Changelog

Covers the whole project: the integration and the cards.

## 0.2.0

Forecasts, a second card, and fixes to the first one.

- The radar card keeps playing after "now" with the Météo-France PIAF nowcast, up to
  3 hours ahead: every 5 minutes for the first hour, then every 15 minutes. Forecast
  images carry a "Forecast +45 min" badge in the title, a "Forecast" banner on the map
  and a dashed outline, and the time slider shows a "now" marker. The new
  `show_forecast` option turns them off. Only the latest forecast run is kept (plus the
  one before it, for a card that is still loading it), outside the size cap.
- New card `custom:meteofrance-rain-bar-card`: one horizontal bar of the rain at the
  home location, from 3 hours ago to midnight (at least 6 hours ahead). The past comes
  from the stored radar history, the next 3 hours from PIAF, then AROME-PI, then
  AROME. Same colours as the radar legend, a "now" line, forecast segments hatched,
  hour labels and a tooltip with the time and rate on each segment. English and French,
  with a visual editor.
- Forecasts are optional. If the key is not subscribed to PIAF, AROME-PI or AROME, the
  radar keeps working, the card and the bar show what they have, and a repair explains
  which API to subscribe to on the portal and that the key must then be regenerated.
  Diagnostics now report the state of each forecast API.
- The radar card's visual editor shows the effective defaults (3 h period, autoplay,
  legend) when an option is unset, instead of empty or off fields.
- Both cards were checked to render in French when Home Assistant is set to French,
  and in English otherwise, with a test for each.
- The radar card fits a half-width column of a sections view: the map scales to the
  card width at 16:9, the controls wrap, and `grid_options` sizing is supported.

## 0.1.0

First release.

- Collects the Météo-France 500 m "lame d'eau" rain mosaic every minute from the
  DPRadar API, using the catalogue's `validity_time` to download each image only once.
  The HDF5 product is decoded in memory and never written to disk.
- Stores one compressed file per 5-minute slot, lossless, in `/media/meteofrance_radar`
  by default. History is thinned as it ages: every image for 3 hours, one per hour up
  to 30 days, one per 3 hours beyond. Images older than 30 days are rewritten as the 12
  display classes. A size cap (500 MB by default) removes the oldest images first.
- Renders PNG layers on demand onto a fixed Web Mercator map of France, one at a time,
  with a disk cache held to 10 % of the cap.
- Lovelace card `custom:meteofrance-radar-card`: play, pause, step, time slider, period
  (3 h, 24 h, 7 days, 30 days, all), mm/h legend, a pin at the home location, and a
  marker in the title when a missing image was skipped. Visual editor for the default
  period, autoplay, legend, frame duration and crossfade. English and French.
- Config flow with the API key checked live, reauth, reconfigure, and an options flow
  for the storage folder and the size cap. A repair shows up two weeks before the key
  expires. Changing the key or reinstalling keeps the history.
- Diagnostics with the key redacted. The key never reaches the log.
