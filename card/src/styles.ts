import { css } from "lit";

export const cardStyles = css`
  :host {
    display: block;
    height: 100%;
  }
  ha-card {
    overflow: hidden;
    padding-bottom: 8px;
    box-sizing: border-box;
  }
  ha-card.fill {
    height: 100%;
    display: flex;
    flex-direction: column;
  }
  ha-card.fill > * {
    flex: none;
  }
  :host([panel]) {
    height: auto;
  }
  /* Alone in a panel view: never taller than the viewport under the HA header. The
     stage is the only flex item allowed to shrink, so the controls stay visible. */
  ha-card.panel {
    display: flex;
    flex-direction: column;
    max-height: calc(
      100dvh - var(--header-height, 56px) - env(safe-area-inset-top, 0px) -
        env(safe-area-inset-bottom, 0px)
    );
  }
  ha-card.panel > * {
    flex: none;
  }
  .title {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 4px 10px;
    padding: 12px 16px 8px;
    font-size: 1.1rem;
    color: var(--primary-text-color);
  }
  .time {
    font-weight: 500;
    font-variant-numeric: tabular-nums;
  }
  .credit {
    font-size: 0.85rem;
    color: var(--secondary-text-color);
  }
  .badge {
    font-size: 0.8rem;
    font-weight: 500;
    padding: 1px 8px;
    border-radius: 10px;
    border: 1px dashed var(--primary-color, #03a9f4);
    color: var(--primary-color, #03a9f4);
  }
  .gap {
    font-size: 0.8rem;
    padding: 1px 8px;
    border-radius: 10px;
    background: var(--warning-color, #ffa600);
    color: var(--text-primary-color, #fff);
  }
  .stage {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    background: #eef0f2;
  }
  .map {
    position: relative;
    width: 100%;
    height: 100%;
  }
  ha-card.fill .stage {
    flex: 1 1 auto;
    min-height: 0;
    aspect-ratio: auto;
    container-type: size;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  ha-card.panel .stage {
    flex: 0 1 auto;
    min-height: 0;
    container-type: size;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  ha-card.fill .map,
  ha-card.panel .map {
    width: min(100cqw, calc(100cqh * var(--map-aspect, 16 / 9)));
    height: auto;
    aspect-ratio: var(--map-aspect, 16 / 9);
  }
  .stage.forecast .map {
    outline: 2px dashed var(--primary-color, #03a9f4);
    outline-offset: -2px;
  }
  .banner {
    position: absolute;
    top: 8px;
    left: 8px;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: 500;
    background: var(--primary-color, #03a9f4);
    color: var(--text-primary-color, #fff);
    pointer-events: none;
  }
  canvas {
    display: block;
    width: 100%;
    height: 100%;
  }
  .pin {
    position: absolute;
    width: 14px;
    height: 14px;
    margin: -7px 0 0 -7px;
    border-radius: 50%;
    background: var(--accent-color, #ff5722);
    border: 2px solid #fff;
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.45);
    box-sizing: border-box;
    pointer-events: none;
  }
  .pin[hidden] {
    display: none;
  }
  .message {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
    text-align: center;
    background: rgba(255, 255, 255, 0.72);
    color: #333;
  }
  .message.error {
    color: var(--error-color, #db4437);
  }
  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px;
    padding: 8px 12px 0;
  }
  .controls button {
    flex: none;
  }
  .slider {
    position: relative;
    flex: 1 1 140px;
    min-width: 0;
    display: flex;
    align-items: center;
  }
  .slider input[type="range"] {
    width: 100%;
    min-width: 0;
    margin: 0;
  }
  /* Inset by half a thumb, so a percentage lines up with the thumb centre. */
  .marks {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 8px;
    right: 8px;
    pointer-events: none;
  }
  .forecast-track {
    position: absolute;
    top: 50%;
    right: 0;
    height: 6px;
    transform: translateY(-50%);
    border-radius: 3px;
    background: var(--primary-color, #03a9f4);
    opacity: 0.25;
  }
  .now-marker {
    position: absolute;
    top: 15%;
    bottom: 15%;
    width: 2px;
    margin-left: -1px;
    background: var(--primary-text-color, #212121);
  }
  button {
    font: inherit;
    cursor: pointer;
    border: none;
    background: none;
    color: var(--primary-text-color);
    border-radius: 6px;
    padding: 4px 8px;
  }
  button:disabled {
    cursor: default;
    opacity: 0.4;
  }
  button.icon {
    font-size: 1.1rem;
    min-width: 36px;
  }
  .periods {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 8px 16px 0;
  }
  .chip {
    font-size: 0.85rem;
    border: 1px solid var(--divider-color, #ccc);
    border-radius: 14px;
    padding: 2px 12px;
  }
  .chip[aria-pressed="true"] {
    background: var(--primary-color, #03a9f4);
    border-color: var(--primary-color, #03a9f4);
    color: var(--text-primary-color, #fff);
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px 8px;
    padding: 10px 16px 0;
    font-size: 0.75rem;
    color: var(--secondary-text-color);
  }
  .legend-unit {
    font-weight: 500;
  }
  .legend-item {
    display: inline-flex;
    align-items: center;
    gap: 3px;
  }
  .swatch {
    width: 12px;
    height: 12px;
    border-radius: 2px;
    border: 1px solid rgba(0, 0, 0, 0.15);
  }
  .attribution {
    padding: 8px 16px 0;
    font-size: 0.7rem;
    color: var(--secondary-text-color);
  }
`;
