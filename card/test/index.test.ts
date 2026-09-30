// @vitest-environment jsdom
import { describe, expect, it } from "vitest";

import { CARD_TAG, RAIN_BAR_TAG } from "../src/index";

describe("card bundle entry", () => {
  it("names and defines both custom elements", () => {
    expect(CARD_TAG).toBe("meteofrance-radar-card");
    expect(RAIN_BAR_TAG).toBe("meteofrance-rain-bar-card");
    expect(customElements.get(CARD_TAG)).toBeTruthy();
    expect(customElements.get(RAIN_BAR_TAG)).toBeTruthy();
  });
});
