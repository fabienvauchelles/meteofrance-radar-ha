import { css } from "lit";

export const rainBarStyles = css`
  :host {
    display: block;
  }
  ha-card {
    padding: 12px 16px 10px;
    box-sizing: border-box;
    height: 100%;
  }
  .title {
    margin: 0 0 8px;
    font-size: 1rem;
    font-weight: 500;
    color: var(--primary-text-color);
  }
  .bar {
    position: relative;
    height: 28px;
    border-radius: 6px;
    overflow: hidden;
    background: var(--secondary-background-color, #e5e5e5);
  }
  .segment {
    position: absolute;
    top: 0;
    bottom: 0;
  }
  .segment.nodata {
    opacity: 0.35;
  }
  .segment.forecast {
    background-image: repeating-linear-gradient(
      45deg,
      rgba(255, 255, 255, 0.35) 0 2px,
      transparent 2px 6px
    );
  }
  /* White stripes vanish on a light track, so dry forecast stripes are grey. */
  .segment.forecast.dry {
    background-image: repeating-linear-gradient(
      45deg,
      rgba(128, 128, 128, 0.3) 0 2px,
      transparent 2px 6px
    );
  }
  .now {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 2px;
    margin-left: -1px;
    background: var(--primary-text-color, #212121);
  }
  .ticks {
    position: relative;
    height: 1.2em;
    margin-top: 3px;
    font-size: 0.75rem;
    color: var(--secondary-text-color);
  }
  .tick {
    position: absolute;
    top: 0;
    transform: translateX(-50%);
    white-space: nowrap;
  }
  .tick.first {
    transform: none;
  }
  .tick.last {
    transform: translateX(-100%);
  }
  .message {
    padding: 4px 0;
    color: var(--secondary-text-color);
  }
  .message.error {
    color: var(--error-color, #db4437);
  }
  .credit {
    margin-top: 4px;
    font-size: 0.7rem;
    color: var(--secondary-text-color);
    text-align: right;
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px 8px;
    padding-top: 6px;
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
  }
`;
