# Changelog

Covers the whole project: the integration and the card.

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
