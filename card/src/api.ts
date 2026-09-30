import type { FramesResponse, HomeAssistant, PeriodName } from "./types";

export class RadarApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
  ) {
    super(message);
    this.name = "RadarApiError";
  }
}

/** Client for the integration's HTTP views, always through the signed-in user's token. */
export class RadarApi {
  constructor(private readonly hass: () => HomeAssistant | undefined) {}

  private get client(): HomeAssistant {
    const hass = this.hass();
    if (!hass) throw new RadarApiError("Home Assistant is not connected", null);
    return hass;
  }

  /** Frame list of a period; `callApi` prefixes `/api/`. */
  frames(period: PeriodName): Promise<FramesResponse> {
    return this.client.callApi<FramesResponse>("GET", `meteofrance_radar/frames?period=${period}`);
  }

  /** Any image the integration serves (layer or basemap), as a Blob. */
  async blob(url: string): Promise<Blob> {
    const response = await this.client.fetchWithAuth(url);
    if (!response.ok) throw new RadarApiError(`${url}: HTTP ${response.status}`, response.status);
    return response.blob();
  }
}
