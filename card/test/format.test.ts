import { describe, expect, it } from "vitest";
import { formatSlot } from "../src/format";

describe("formatSlot", () => {
  it("writes the slot in Paris time, French and English style", () => {
    expect(formatSlot("2026-09-30T10:30:00Z", "Europe/Paris", "fr")).toBe("30/09/26 12h30");
    expect(formatSlot("2026-09-30T10:30:00Z", "Europe/Paris", "en")).toBe("30/09/26 12:30");
  });

  it("follows the winter offset and the day change", () => {
    expect(formatSlot("2026-12-31T23:05:00Z", "Europe/Paris", "fr-FR")).toBe("01/01/27 00h05");
  });

  it("uses another zone when Home Assistant is set to one", () => {
    expect(formatSlot("2026-09-30T10:30:00Z", "America/New_York", "en")).toBe("30/09/26 06:30");
    expect(formatSlot("2026-09-30T10:30:00Z", "Asia/Tokyo", "fr")).toBe("30/09/26 19h30");
  });

  it("falls back to English for any other language", () => {
    expect(formatSlot("2026-09-30T10:30:00Z", "UTC", "de")).toBe("30/09/26 10:30");
  });

  it("still formats when the zone name is unknown", () => {
    expect(formatSlot("2026-09-30T10:30:00Z", "Mars/Olympus", "en")).toMatch(
      /^30\/09\/26 \d\d:30$/,
    );
  });
});
