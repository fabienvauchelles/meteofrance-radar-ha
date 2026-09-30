import { html, nothing, type TemplateResult } from "lit";
import { stringsFor } from "../i18n";
import { renderLegend } from "../legend";
import type { RadarLegend } from "../types";
import { hourTicks, percentOf, segmentTooltip, spanBox } from "./geometry";
import type { Language, RainBarStrings } from "./i18n";
import type { PinSegment, PinSeriesResponse } from "./types";

export type BarState = "loading" | "error" | "ready";

const DRY_CLASS = 0;
const NODATA_CLASS = 11;
// Labels this close to an edge are anchored to it so they stay inside the card.
const EDGE_PERCENT = 4;

export interface BarModel {
  strings: RainBarStrings;
  language: Language;
  title: string | null;
  showLegend: boolean;
  state: BarState;
  data: PinSeriesResponse | null;
  /** Client clock, epoch milliseconds. */
  now: number;
  timeZone: string | undefined;
  maxLabels: number;
}

/** Fill colour of a palette class; null for dry (class 0), where the track shows. */
export function segmentColor(cls: number, legend: RadarLegend): string | null {
  if (cls === NODATA_CLASS) return legend.nodata_color;
  if (cls >= 1 && cls <= legend.colors.length) return legend.colors[cls - 1] ?? null;
  return null;
}

function renderSegment(
  segment: PinSegment,
  start: number,
  end: number,
  model: BarModel,
  legend: RadarLegend,
): TemplateResult {
  const from = Date.parse(segment.start);
  const to = Date.parse(segment.end);
  const box = spanBox(from, to, start, end);
  const color = segmentColor(segment.class, legend);
  const classes = [
    "segment",
    segment.source === "radar" ? "observed" : "forecast",
    segment.class === NODATA_CLASS ? "nodata" : "",
    segment.class === DRY_CLASS ? "dry" : "",
  ]
    .filter(Boolean)
    .join(" ");
  const style = `left:${box.left}%;width:${box.width}%${color ? `;background-color:${color}` : ""}`;
  const tip = segmentTooltip(
    from,
    to,
    segment.mm_h,
    model.timeZone,
    model.language,
    model.strings.noData,
  );
  return html`<div
    class=${classes}
    style=${style}
    data-source=${segment.source}
    data-class=${segment.class}
    role="img"
    title=${tip}
    aria-label=${tip}
  ></div>`;
}

function renderTicks(start: number, end: number, model: BarModel): TemplateResult {
  const ticks = hourTicks(start, end, model.timeZone, model.language, model.maxLabels);
  return html`<div class="ticks" aria-hidden="true">
    ${ticks.map((tick) => {
      const edge =
        tick.percent < EDGE_PERCENT ? "first" : tick.percent > 100 - EDGE_PERCENT ? "last" : "";
      return html`<span class="tick ${edge}" style="left:${tick.percent}%">${tick.label}</span>`;
    })}
  </div>`;
}

function renderBar(data: PinSeriesResponse, model: BarModel): TemplateResult {
  const start = Date.parse(data.window.start);
  const end = Date.parse(data.window.end);
  const showNow = model.now >= start && model.now <= end;
  return html`
    <div class="bar" role="group" aria-label=${model.strings.bar}>
      ${data.segments.map((segment) => renderSegment(segment, start, end, model, data.legend))}
      ${
        showNow
          ? html`<div
              class="now"
              style="left:${percentOf(model.now, start, end)}%"
              title=${model.strings.now}
              aria-label=${model.strings.now}
            ></div>`
          : nothing
      }
    </div>
    ${renderTicks(start, end, model)}
    ${
      model.showLegend
        ? renderLegend(data.legend, stringsFor(model.language), model.language)
        : nothing
    }
    <div class="credit">${model.strings.credit(data.attribution)}</div>
  `;
}

function renderBody(model: BarModel): TemplateResult {
  const { data, strings } = model;
  if (data === null) {
    return model.state === "error"
      ? html`<div class="message error" role="alert">${strings.error}</div>`
      : html`<div class="message loading">${strings.loading}</div>`;
  }
  if (!data.located) return html`<div class="message located">${strings.notLocated}</div>`;
  return renderBar(data, model);
}

export function renderRainBar(model: BarModel): TemplateResult {
  return html`
    <ha-card>
      ${model.title ? html`<h2 class="title">${model.title}</h2>` : nothing}
      ${renderBody(model)}
    </ha-card>
  `;
}
