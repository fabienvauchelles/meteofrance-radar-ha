import { html, type TemplateResult } from "lit";
import type { Strings } from "./i18n";
import type { RadarLegend } from "./types";

function levelLabel(level: number, language: "en" | "fr"): string {
  const text = String(level);
  return language === "fr" ? text.replace(".", ",") : text;
}

/**
 * The mm/h scale: one swatch per class, labelled with its lower bound, then the
 * "no data" swatch. The API sends one more level than colours (the upper bound of
 * the last class), which the scale does not draw. Colours come from the API so they
 * always match the layers.
 */
export function renderLegend(
  legend: RadarLegend,
  strings: Pick<Strings, "legend" | "noData">,
  language: "en" | "fr",
): TemplateResult {
  return html`
    <div class="legend" role="list" aria-label=${strings.legend}>
      <span class="legend-unit">${legend.unit}</span>
      ${legend.colors.map(
        (color, index) => html`
          <span class="legend-item" role="listitem">
            <span class="swatch" style="background:${color}"></span>
            <span class="legend-label">${levelLabel(legend.levels[index] ?? 0, language)}</span>
          </span>
        `,
      )}
      <span class="legend-item" role="listitem">
        <span class="swatch" style="background:${legend.nodata_color}"></span>
        <span class="legend-label">${strings.noData}</span>
      </span>
    </div>
  `;
}
