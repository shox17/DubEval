// Dev tool: writes dubeval/language_names.json, every speech language's name in each interface language, from the
// Unicode CLDR names built into Node (Intl.DisplayNames). The app reads the file; it needs no Node or ICU at run time.
//   node tools/build_language_names.mjs
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const source = readFileSync(join(root, "dubeval", "languages.py"), "utf8");
const codes = [...source.matchAll(/^\s+"([a-z]{2,3})": "/gm)].map(m => m[1]);
const ISO = { jw: "jv" };                     // Whisper's code for Javanese; CLDR knows it as jv
const UI = ["en", "ko", "pt", "es"];
const out = {};
for (const ui of UI) {
  const names = new Intl.DisplayNames([ui], { type: "language", fallback: "none" });
  out[ui] = {};
  for (const code of codes) {
    const name = names.of(ISO[code] || code);
    if (name) out[ui][code] = name;          // as each language writes it in a sentence (pt/es: lower case)
  }
}
writeFileSync(join(root, "dubeval", "language_names.json"), JSON.stringify(out, null, 1) + "\n", "utf8");
console.log(`${codes.length} languages; named: ${UI.map(ui => `${ui} ${Object.keys(out[ui]).length}`).join(", ")}`);
