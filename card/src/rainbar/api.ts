import type { HomeAssistant } from "../types";
import type { PinSeriesResponse } from "./types";

export const PIN_SERIES_PATH = "meteofrance_radar/pin_series";

/** Rain series at the home pin, fetched with the signed-in user's token (`callApi` adds `/api/`). */
export function fetchPinSeries(hass: HomeAssistant): Promise<PinSeriesResponse> {
  return hass.callApi<PinSeriesResponse>("GET", PIN_SERIES_PATH);
}
