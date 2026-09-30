import { readFileSync } from "node:fs";

import { nodeResolve } from "@rollup/plugin-node-resolve";
import terser from "@rollup/plugin-terser";
import typescript from "@rollup/plugin-typescript";

// package.json is the card's single version source; the console banner is written
// at build time so no TypeScript file carries a version literal.
const { version } = JSON.parse(readFileSync("./package.json", "utf8"));
const BANNER =
  `console.info("%c METEOFRANCE-RADAR-CARD %c ${version} ",` +
  ` "background:#1f5fa8;color:#fff;border-radius:3px", "");`;

const OUT_DIR = "../custom_components/meteofrance_radar/www";

// One ES module, no code splitting: the integration serves a single file and
// registers it as a Lovelace resource. The bundle is committed, CI checks it is
// fresh, and the release workflow rebuilds it into the zip.
export default {
  input: "src/index.ts",
  output: {
    file: `${OUT_DIR}/meteofrance-radar-card.js`,
    format: "es",
    sourcemap: false,
    inlineDynamicImports: true,
    banner: BANNER,
  },
  plugins: [
    nodeResolve(),
    typescript({
      tsconfig: "./tsconfig.json",
      exclude: ["test/**/*", "**/*.test.ts", "vitest.config.ts"],
      // outDir must sit under the bundle's directory for the plugin's path check;
      // rollup pipes the emit, nothing extra is written there.
      compilerOptions: {
        declaration: false,
        declarationMap: false,
        sourceMap: false,
        outDir: OUT_DIR,
      },
    }),
    terser({ format: { comments: false } }),
  ],
};
