import { css } from "lit";

export const cardStyles = css`
  :host {
    display: block;
  }
  ha-card {
    overflow: hidden;
    padding-bottom: 8px;
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
    align-items: center;
    gap: 4px;
    padding: 8px 12px 0;
  }
  .controls input[type="range"] {
    flex: 1;
    min-width: 0;
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
