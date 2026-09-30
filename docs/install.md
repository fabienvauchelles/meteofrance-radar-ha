# Install

Four steps: get an API key from Météo-France, install the integration through HACS,
add it with the key, then put the cards on a dashboard. Written against Home Assistant
2026.8.

## 1. The Météo-France API key

The radar comes from Météo-France's public API. Access is free but needs an account
and a key.

1. Create an account on [portail-api.meteofrance.fr](https://portail-api.meteofrance.fr)
   and confirm the email.
2. In the API catalogue, open **DPRadar** and subscribe to it.
3. Generate an API key for that subscription. Pick the longest validity the portal
   offers (one year at the time of writing).
4. Copy the key. The portal also shows an OAuth2 token flow: you do not need it. The
   integration sends the key as it is, in an `apikey` header.

### Optional: forecast subscriptions

The forecasts on the radar card and the rain bar card come from three more APIs on
the same portal. They are free and each is optional. Subscribe, from the same
application as DPRadar, to the ones you want:

1. **PrevisionImmediatePrecipitations**, labelled "Modèle AROME Prévision Immédiate
   Agrégée Fusionnée (PIAF)": the forecast images on the radar card and the first
   3 hours of the rain bar. It downloads about 280 MB per hour.
2. **AROME-PI**, "Modèle AROME Prévision Immédiate": the rain bar from +3 h to +6 h.
3. **AROME**, "Modèle AROME": the rain bar after +6 h, up to midnight.

Subscribe first, then generate the key: a key only knows the subscriptions that
existed when it was made. If you add a subscription later, generate a new key and
enter it with Reconfigure (see [Renewing the API key](#renewing-the-api-key)).

The key is a long string with two dots in it. Treat it like a password. The
integration stores it in the config entry, never writes it to the log, and redacts
it from diagnostics.

## 2. The integration (HACS)

The integration is not in the default HACS list. It installs as a custom repository.

1. HACS > top-right menu > Custom repositories. Add
   `https://github.com/fabienvauchelles/meteofrance-radar-ha`, category
   **Integration**.
2. Download **Météo-France Radar**.
3. **Restart Home Assistant Core** (Settings > System > Restart). A new integration is
   not loaded by a config reload.

On the first start after the download, Home Assistant installs `h5py` from PyPI, the
library that reads the radar files. It is a few megabytes and needs internet access.

## 3. Add the integration

1. Settings > Devices & Services > Add integration > **Météo-France Radar**.
2. Paste the API key and submit.

The key is checked before anything is saved: an expired key, a key the API refuses,
or an API that cannot be reached each give their own message, and nothing is created.
Only the radar API is checked here. The forecast APIs are tried once the integration
is running, and a missing subscription shows up as a repair (see below), not as an
error in this form.

Once added, the integration asks Météo-France for a new image every minute. The first
one is stored within a few minutes. There is nothing to see under the integration: no
device, no entity. Everything goes through the card.

### Where the images go

By default in `/media/meteofrance_radar`, next to your media folder, not in `/config`.
That keeps them out of Home Assistant backups, which would otherwise grow by hundreds
of megabytes. To store them elsewhere, open the integration's options (Configure):

- **Storage folder**: any absolute path Home Assistant can write to, for example a
  mounted network share or a second disk. The folder is created if it does not exist.
  Existing images are not moved: the old folder is left as it is.
- **Size cap**: how much disk the images may use, 500 MB by default. See
  [`data-and-storage.md`](data-and-storage.md) for what fits.

Saving the options reloads the integration.

## 4. The cards

The integration registers both cards by itself, so there is no resource to add and no
file to copy.

1. Open a dashboard and click Edit (the pencil), then Add card.
2. Search for **Météo-France Radar** (the animated map) or **Météo-France Rain Bar**
   (the rain at home as one bar) and pick it. If it is not in the list, reload the
   browser tab once: the browser still has the page from before the install.
3. Set the options in the visual editor, or leave the defaults, and save.

The card in YAML:

```yaml
type: custom:meteofrance-radar-card
default_period: 3h
autoplay: true
show_legend: true
frame_duration_ms: 500
crossfade_ms: 300
show_forecast: true
```

The rain bar card in YAML:

```yaml
type: custom:meteofrance-rain-bar-card
title: Rain at home
show_legend: false
```

The card uses the home location from Settings > System > General for the pin, and
the language and time zone of Home Assistant for its text and the time in the title.
If no home location is set, there is no pin, and the rain bar asks you to set one.

### Dashboards in YAML mode

If your Lovelace resources are declared in `configuration.yaml` rather than in the UI,
Home Assistant does not let an integration add one. Add it yourself:

```yaml
lovelace:
  resources:
    - url: /meteofrance_radar/meteofrance-radar-card.js
      type: module
```

At startup the integration logs an `info` line with that URL when it finds Lovelace in
YAML mode.

## Renewing the API key

Two weeks before the key expires, Settings > System > Repairs shows **Météo-France API
key expires soon**, with the date. Generate a new key on the portal, open the repair,
and paste the new key when asked.

If the key has already expired, or Météo-France starts refusing it, Home Assistant
shows the integration as needing attention (Reconfigure on its card in Devices &
Services). Collection stops until a new key is entered. Images missed in the meantime
are lost, but everything stored before is kept.

To change the key at any time: Settings > Devices & Services > Météo-France Radar >
three-dot menu > Reconfigure. This is also how a new key with more subscriptions is
entered.

## Missing forecast subscriptions

When a forecast API refuses the key, Settings > System > Repairs shows one repair per
API, naming the portal API to subscribe to. The radar keeps working; the radar card
stops at "now" and the rain bar shows only what it has. To fix it:

1. On the portal, subscribe to the API named in the repair.
2. Generate a new key: the old one does not gain the new subscription.
3. Reconfigure the integration with the new key.

Reconfigure reloads the integration, which tries every forecast API again straight
away, and the repair clears itself once the API answers. Without a new key, a
refused API is tried again every hour. If you do not want that forecast, you can leave
the repair as it is: nothing else depends on it.

## Removing it

Deleting the integration stops the collection and removes the entry. It does not
delete the stored images: reinstall later with the same storage folder and the
history comes back. To free the space, delete the storage folder by hand.

## When something looks wrong

- **The card says there is no radar image yet.** Wait five minutes after adding the
  integration. If it stays empty, check Settings > System > Logs for
  `meteofrance_radar` lines.
- **"Custom element doesn't exist: meteofrance-radar-card".** Reload the browser tab.
  In YAML mode, check the resource above.
- **Gaps in the animation.** A missed image cannot be fetched again (see
  [`data-and-storage.md`](data-and-storage.md)). Gaps usually line up with Home
  Assistant restarts or a Météo-France outage.
- **Diagnostics.** Settings > Devices & Services > Météo-France Radar > three-dot menu
  > Download diagnostics. It holds the storage state, the last collector pass and the
  state of each forecast API, with the key redacted and no home location.
- **No forecast on the card.** Check Settings > System > Repairs for a missing
  subscription. Right after a start, the first forecast run takes a few minutes to
  arrive.
