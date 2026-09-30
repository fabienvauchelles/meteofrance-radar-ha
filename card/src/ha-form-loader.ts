// Home Assistant loads ha-form lazily, only once a built-in editor has been opened.
// Asking a built-in card for its editor makes the frontend load it (the approach
// mushroom uses); the wait is capped so the editor opens anyway, and HA falls back to
// its YAML editor when ha-form never shows up.

export const HA_FORM_TAG = "ha-form";
export const HA_FORM_WAIT_MS = 5000;
const DONOR_CARD_TAG = "hui-tile-card";

type EditorHost = { getConfigElement?: () => Promise<unknown> | unknown };

export async function ensureHaForm(
  registry: CustomElementRegistry = customElements,
  waitMs = HA_FORM_WAIT_MS,
): Promise<void> {
  if (registry.get(HA_FORM_TAG)) return;
  const donor = registry.get(DONOR_CARD_TAG) as unknown as EditorHost | undefined;
  try {
    await donor?.getConfigElement?.();
  } catch (error) {
    console.warn("meteofrance-radar-card: could not preload the form editor", error);
  }
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<void>((resolve) => {
    timer = setTimeout(resolve, waitMs);
  });
  await Promise.race([registry.whenDefined(HA_FORM_TAG).then(() => undefined), timeout]);
  clearTimeout(timer);
}
