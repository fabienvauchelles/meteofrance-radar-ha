import { describe, expect, it } from "vitest";

import { CARD_TAG } from "../src/index";

describe("card bundle entry", () => {
  it("names the custom element", () => {
    expect(CARD_TAG).toBe("meteofrance-radar-card");
  });
});
