import { html, nothing, type TemplateResult } from "lit";
import { type Ref, ref } from "lit/directives/ref.js";
import { styleMap } from "lit/directives/style-map.js";
import type { Language, Strings } from "./i18n";
import { renderLegend } from "./legend";
import { type FramesResponse, PERIODS, type PeriodName, type RadarLegend } from "./types";

export type LoadState = "loading" | "ready" | "empty" | "error";

export interface ViewModel {
  strings: Strings;
  language: Language;
  state: LoadState;
  /** Formatted time of the frame on screen, null before the first draw. */
  time: string | null;
  gapMin: number;
  /** Minutes after "now" when a forecast frame is on screen, else null. */
  leadMin: number | null;
  /** Slider position of the "now" marker in percent, null without forecast frames. */
  nowPct: number | null;
  /** The dashboard gives the card a fixed height (numeric grid rows). */
  fill: boolean;
  /** The card is alone in a panel view and must fit under the header. */
  panel: boolean;
  playing: boolean;
  waiting: boolean;
  position: number;
  count: number;
  period: PeriodName;
  /** Pin position as percentages of the map, null when hidden. */
  pin: { left: number; top: number } | null;
  /** Map width / height, so the pin percentages land on the canvas pixels. */
  aspect: number;
  legend: RadarLegend | null;
  attribution: { radar: string; basemap: string } | null;
}

export interface ViewHandlers {
  canvasRef: Ref<HTMLCanvasElement>;
  togglePlay(): void;
  step(delta: number): void;
  scrub(index: number): void;
  scrubEnd(): void;
  selectPeriod(period: PeriodName): void;
}

/** Pin position as percentages of the map; null when unknown or outside the map. */
export function pinPosition(data: FramesResponse | null): { left: number; top: number } | null {
  const pin = data?.pin;
  if (!data || !pin?.inside) return null;
  return { left: (pin.x / data.grid.width) * 100, top: (pin.y / data.grid.height) * 100 };
}

function renderTitle(vm: ViewModel): TemplateResult {
  const { strings } = vm;
  return html`
    <div class="title">
      ${vm.time ? html`<span class="time">${vm.time}</span>` : nothing}
      ${
        vm.leadMin !== null
          ? html`<span class="badge">${strings.forecastLead(vm.leadMin)}</span>`
          : nothing
      }
      <span class="credit">${strings.credit}</span>
      ${vm.gapMin > 0 ? html`<span class="gap" role="note">${strings.gap(vm.gapMin)}</span>` : nothing}
    </div>
  `;
}

function renderMessage(vm: ViewModel): TemplateResult | typeof nothing {
  const { strings } = vm;
  if (vm.state === "loading") return html`<div class="message">${strings.loading}</div>`;
  if (vm.state === "empty") return html`<div class="message empty">${strings.empty}</div>`;
  if (vm.state === "error") {
    return html`<div class="message error" role="alert">${strings.error}</div>`;
  }
  return nothing;
}

function renderStage(vm: ViewModel, handlers: ViewHandlers): TemplateResult {
  const pin = vm.pin;
  const pinStyle = pin ? { left: `${pin.left}%`, top: `${pin.top}%` } : {};
  // In fill mode the stage takes the height left by the controls and the map keeps
  // its own ratio inside it, so the pin percentages still land on the right pixel.
  // In a panel the stage starts at the map ratio and may only shrink from there.
  const aspect = String(vm.aspect);
  const stageStyle = vm.fill
    ? { "--map-aspect": aspect }
    : { "aspect-ratio": aspect, "--map-aspect": aspect };
  const forecast = vm.leadMin !== null;
  return html`
    <div class="stage ${forecast ? "forecast" : ""}" style=${styleMap(stageStyle)}>
      <div class="map">
        <canvas ${ref(handlers.canvasRef)}></canvas>
        <div
          class="pin"
          title=${vm.strings.pin}
          ?hidden=${pin === null}
          style=${styleMap(pinStyle)}
        ></div>
        ${forecast ? html`<div class="banner" role="note">${vm.strings.forecast}</div>` : nothing}
      </div>
      ${renderMessage(vm)}
    </div>
  `;
}

function renderSlider(vm: ViewModel, handlers: ViewHandlers, disabled: boolean): TemplateResult {
  const nowPct = vm.nowPct;
  return html`
    <div class="slider">
      <input
        type="range"
        min="0"
        max=${Math.max(0, vm.count - 1)}
        step="1"
        aria-label=${vm.strings.timeSlider}
        ?disabled=${disabled}
        .value=${String(vm.position)}
        @input=${(event: Event) => handlers.scrub(Number((event.target as HTMLInputElement).value))}
        @change=${handlers.scrubEnd}
      />
      ${
        nowPct !== null
          ? html`<div class="marks">
              <div class="forecast-track" style=${styleMap({ left: `${nowPct}%` })}></div>
              <div
                class="now-marker"
                title=${vm.strings.now}
                style=${styleMap({ left: `${nowPct}%` })}
              ></div>
            </div>`
          : nothing
      }
    </div>
  `;
}

function renderControls(vm: ViewModel, handlers: ViewHandlers): TemplateResult {
  const { strings } = vm;
  const disabled = vm.count === 0;
  return html`
    <div class="controls">
      <button
        class="icon play"
        ?disabled=${disabled}
        aria-label=${vm.playing ? strings.pause : strings.play}
        title=${vm.playing ? strings.pause : strings.play}
        @click=${handlers.togglePlay}
      >${vm.playing ? "⏸" : "▶"}</button>
      <button
        class="icon back"
        ?disabled=${disabled}
        aria-label=${strings.stepBack}
        title=${strings.stepBack}
        @click=${() => handlers.step(-1)}
      >⏮</button>
      <button
        class="icon forward"
        ?disabled=${disabled}
        aria-label=${strings.stepForward}
        title=${strings.stepForward}
        @click=${() => handlers.step(1)}
      >⏭</button>
      ${renderSlider(vm, handlers, disabled)}
    </div>
  `;
}

function renderPeriods(vm: ViewModel, handlers: ViewHandlers): TemplateResult {
  return html`
    <div class="periods" role="group" aria-label=${vm.strings.periodGroup}>
      ${PERIODS.map(
        (period) => html`
          <button
            class="chip"
            data-period=${period}
            aria-pressed=${vm.period === period ? "true" : "false"}
            @click=${() => handlers.selectPeriod(period)}
          >${vm.strings.periods[period]}</button>
        `,
      )}
    </div>
  `;
}

export function renderCard(vm: ViewModel, handlers: ViewHandlers): TemplateResult {
  const attribution = vm.attribution;
  return html`
    <ha-card class=${vm.panel ? "panel" : vm.fill ? "fill" : ""}>
      ${renderTitle(vm)} ${renderStage(vm, handlers)} ${renderControls(vm, handlers)}
      ${renderPeriods(vm, handlers)}
      ${vm.legend ? renderLegend(vm.legend, vm.strings, vm.language) : nothing}
      ${
        attribution
          ? html`<div class="attribution">
              ${vm.strings.attribution(attribution.radar, attribution.basemap)}
            </div>`
          : nothing
      }
    </ha-card>
  `;
}
