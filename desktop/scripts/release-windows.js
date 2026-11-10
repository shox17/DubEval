// A signed Windows release, in two commands around the company signing portal (the signing key never leaves it, so
// signing can't be part of the build):
//
//   npm run build:windows:release     builds the installer, copies it to <codesign>\Before_Sign\DubEval-Setup-<v>-unsigned.exe
//                                     and prints what to do in the portal
//   (portal, by hand, from the VDI)   upload it, sign it, download the signed file into <codesign>\After_Sign\
//   npm run release:windows:finish    checks the signature, puts the signed installer in dist/ as DubEval-Setup.exe and
//                                     rebuilds latest.yml and the .blockmap from it, then prints what to upload
//
// The finish step is required. Signing changes the installer's bytes: with the build's latest.yml every installed app
// refuses the update ("sha512 checksum mismatch", tested 2026-11-10). And because the app carries publisherName
// (package.json build.win.signtoolOptions), from the first signed release on an update must be signed by that exact
// publisher, so this refuses anything not validly signed by it. Never publish an installer this didn't finish.
//
// Settings: codesign.local.json next to package.json (git-ignored) or environment variables; the portal's address is
// internal, so it never goes in the repository:
//   { "dir": "C:\\dubeval_windows_codesign", "vdiDrive": "Z:", "portal": "<portal address>" }
//   DUBEVAL_CODESIGN_DIR, DUBEVAL_CODESIGN_VDI_DRIVE, DUBEVAL_CODESIGN_PORTAL
const { spawnSync } = require("node:child_process");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const DESKTOP = path.resolve(__dirname, "..");
const DIST = path.join(DESKTOP, "dist");
const INSTALLER = "DubEval-Setup.exe";
const pkg = JSON.parse(fs.readFileSync(path.join(DESKTOP, "package.json"), "utf8"));
const VERSION = pkg.version;
const PUBLISHER = (pkg.build.win.signtoolOptions || {}).publisherName?.[0];

function settings() {
  let local = {};
  const file = path.join(DESKTOP, "codesign.local.json");
  if (fs.existsSync(file)) local = JSON.parse(fs.readFileSync(file, "utf8"));
  return {
    dir: process.env.DUBEVAL_CODESIGN_DIR || local.dir || "C:\\dubeval_windows_codesign",
    vdiDrive: process.env.DUBEVAL_CODESIGN_VDI_DRIVE || local.vdiDrive || "Z:",
    portal: process.env.DUBEVAL_CODESIGN_PORTAL || local.portal || null,
  };
}

// The same folder as the VDI sees it: this PC's C: is mapped there as another drive (\\tsclient\C → Z:).
const inVdi = (p, drive) => p.replace(/^[A-Za-z]:/, drive);

function fail(message) {
  console.error(`\n✗ ${message}\n`);
  process.exit(1);
}

function step(n, text) {
  console.log(`\n── ${n}. ${text}`);
}

function readYaml(file) {
  return require("js-yaml").load(fs.readFileSync(file, "utf8"));
}

function sha512(file) {
  return crypto.createHash("sha512").update(fs.readFileSync(file)).digest("base64");
}

// ---------- build ----------
function build() {
  const cfg = settings();
  if (!PUBLISHER) fail("package.json has no build.win.signtoolOptions.publisherName: set the certificate's publisher name first.");
  step(1, `Check the bundled Python is this version's (${VERSION})`);
  const buildInfo = path.join(DESKTOP, "resources", "build.json");
  if (!fs.existsSync(buildInfo)) fail("desktop/resources is missing: run `python tools/build_desktop.py` from the project folder first.");
  const bundled = JSON.parse(fs.readFileSync(buildInfo, "utf8")).dubeval;
  if (bundled !== VERSION) fail(`desktop/resources holds DubEval ${bundled}, not ${VERSION}: run \`python tools/build_desktop.py\` again.`);
  console.log(`   resources/build.json: DubEval ${bundled} ✓`);

  step(2, "Build the unsigned installer (electron-builder, no publishing)");
  const cli = require.resolve("electron-builder/cli.js");
  const run = spawnSync(process.execPath, [cli, "--win", "nsis", "--publish", "never"], { cwd: DESKTOP, stdio: "inherit" });
  if (run.status !== 0) fail(`electron-builder failed (exit ${run.status}).`);
  const latest = readYaml(path.join(DIST, "latest.yml"));
  if (latest.version !== VERSION) fail(`dist/latest.yml says ${latest.version}, not ${VERSION}.`);

  step(3, "Copy it to the signing folder");
  const before = path.join(cfg.dir, "Before_Sign");
  const after = path.join(cfg.dir, "After_Sign");
  fs.mkdirSync(before, { recursive: true });
  fs.mkdirSync(after, { recursive: true });
  const name = `DubEval-Setup-${VERSION}-unsigned.exe`;
  fs.copyFileSync(path.join(DIST, INSTALLER), path.join(before, name));
  const mb = (fs.statSync(path.join(before, name)).size / 1e6).toFixed(1);
  console.log(`   ${path.join(before, name)} (${mb} MB)`);

  step(4, "Sign it in the portal (you, from the VDI)");
  const portal = cfg.portal || "the company code-signing portal (put its address in codesign.local.json → portal)";
  console.log(`   a. In the VDI, open ${portal} and sign in.
   b. Optional, the first time: create a folder named "dubeval" (새폴더 → 생성) and open it, so DubEval's files stay apart.
   c. 파일 선택 → ${inVdi(path.join(before, name), cfg.vdiDrive)} → 파일 업로드.
   d. Select the uploaded file in the list → 다운로드, and save it in ${inVdi(after, cfg.vdiDrive)}\\
      (keep the file name; any name starting with DubEval-Setup-${VERSION} works).
   e. Check it here (Status should be Valid, signer ${PUBLISHER}):
      Get-AuthenticodeSignature -FilePath "${path.join(after, name)}"`);

  step(5, "Then finish the release");
  console.log(`   npm run release:windows:finish
   It checks the signature, puts the signed installer in dist/ and rebuilds latest.yml and the .blockmap from it.
   Don't upload dist/ before that: installed apps would refuse the update.\n`);
}

// ---------- finish ----------
function signedFile(cfg, given) {
  if (given) return path.resolve(given);
  const after = path.join(cfg.dir, "After_Sign");
  const pattern = new RegExp(`^DubEval-Setup-${VERSION.replace(/\./g, "\\.")}.*\\.exe$`, "i");
  const found = (fs.existsSync(after) ? fs.readdirSync(after) : [])
    .filter(f => pattern.test(f))
    .map(f => path.join(after, f))
    .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  if (!found.length) fail(`No signed installer in ${after} (a file named DubEval-Setup-${VERSION}…exe). Sign it in the portal first.`);
  return found[0];
}

function signature(file) {
  const quoted = file.replace(/'/g, "''");
  const script = `$s = Get-AuthenticodeSignature -LiteralPath '${quoted}'; $c = $s.SignerCertificate;
    [pscustomobject]@{ status = $s.Status.ToString(); message = $s.StatusMessage; subject = $c.Subject; issuer = $c.Issuer;
      notAfter = if ($c) { $c.NotAfter.ToString('yyyy-MM-dd') } else { $null }; thumbprint = $c.Thumbprint;
      timestamped = [bool]$s.TimeStamperCertificate; product = (Get-Item -LiteralPath '${quoted}').VersionInfo.ProductVersion
    } | ConvertTo-Json -Compress`;
  const run = spawnSync("powershell.exe", ["-NoProfile", "-NonInteractive", "-Command", script], { encoding: "utf8" });
  if (run.status !== 0) fail(`Couldn't read the signature: ${run.stderr || run.stdout}`);
  return JSON.parse(run.stdout);
}

async function finish() {
  const cfg = settings();
  const args = process.argv.slice(3);
  const allowNoTimestamp = args.includes("--allow-no-timestamp");
  const file = signedFile(cfg, args.find(a => !a.startsWith("--")));
  const unsigned = path.join(DIST, INSTALLER);
  if (!fs.existsSync(unsigned)) fail("dist/DubEval-Setup.exe is missing: run npm run build:windows:release first.");
  const latestFile = path.join(DIST, "latest.yml");
  const latest = readYaml(latestFile);
  if (latest.version !== VERSION) fail(`dist/latest.yml is for ${latest.version}, not ${VERSION}: build again.`);

  step(1, `Check the signature of ${path.basename(file)}`);
  const sig = signature(file);
  const cn = (/(?:^|,\s*)CN=("?)([^,"]+)\1/.exec(sig.subject || "") || [])[2];
  console.log(`   status ${sig.status} · signer ${sig.subject || "none"}\n   issuer ${sig.issuer || "-"} · valid until ${sig.notAfter || "-"} · timestamped ${sig.timestamped}`);
  if (sig.status !== "Valid") fail(`The signature isn't valid (${sig.status}: ${sig.message}). Sign it again in the portal.`);
  if (cn !== PUBLISHER) fail(`It's signed by "${cn}", but the app expects "${PUBLISHER}" (package.json build.win.signtoolOptions.publisherName).
  Installed apps of this version would refuse every later update. Set publisherName to "${cn}", build again and sign the new file.`);
  if (!sig.timestamped && !allowNoTimestamp) fail("The signature has no timestamp, so it stops being valid when the certificate expires. Ask for a timestamped signature (or rerun with --allow-no-timestamp).");
  if (!String(sig.product || "").startsWith(VERSION)) fail(`The signed file is version ${sig.product}, not ${VERSION}: it isn't this build.`);
  const grew = fs.statSync(file).size - fs.statSync(unsigned).size;
  if (grew <= 0 || grew > 256 * 1024) fail(`The signed file is ${grew} bytes larger than this build's installer: it isn't this build signed.`);
  console.log(`   ✓ valid, signed by ${PUBLISHER}, timestamped, version ${sig.product}, ${grew} bytes of signature`);

  step(2, "Put the signed installer in dist/ (the unsigned one is kept in dist/unsigned/)");
  fs.mkdirSync(path.join(DIST, "unsigned"), { recursive: true });
  for (const f of [INSTALLER, `${INSTALLER}.blockmap`, "latest.yml"]) {
    if (fs.existsSync(path.join(DIST, f))) fs.copyFileSync(path.join(DIST, f), path.join(DIST, "unsigned", f));
  }
  fs.copyFileSync(file, unsigned);

  step(3, "Rebuild the .blockmap and latest.yml from the signed file");
  const { buildBlockMap } = require("app-builder-lib/out/targets/blockmap/blockmap");
  const info = await buildBlockMap(unsigned, "gzip", `${unsigned}.blockmap`);
  for (const f of latest.files) {
    f.sha512 = info.sha512;
    f.size = info.size;
    if (info.blockMapSize) f.blockMapSize = info.blockMapSize;
  }
  latest.sha512 = info.sha512;
  fs.writeFileSync(latestFile, require("js-yaml").dump(latest, { lineWidth: -1 }));
  if (sha512(unsigned) !== latest.sha512) fail("latest.yml doesn't match the signed installer after rebuilding it.");
  console.log(`   latest.yml: ${VERSION}, ${info.size} bytes, sha512 ${info.sha512.slice(0, 16)}… ✓ matches the signed installer`);

  const notes = JSON.parse(fs.readFileSync(path.join(DESKTOP, "..", "dubeval", "release_notes.json"), "utf8"))[VERSION];
  if (notes?.en?.length) fs.writeFileSync(path.join(DIST, "release-notes.md"), notes.en.map(l => `- ${l}`).join("\n") + "\n");
  fs.writeFileSync(path.join(DIST, "signing.json"), JSON.stringify({ version: VERSION, signedFile: path.basename(file),
    signer: sig.subject, issuer: sig.issuer, thumbprint: sig.thumbprint, notAfter: sig.notAfter, timestamped: sig.timestamped,
    size: info.size, sha512: info.sha512, finished: new Date().toISOString() }, null, 2));

  step(4, "Ready to publish (nothing is uploaded by this script)");
  console.log(`   Upload these three together as the GitHub release v${VERSION} (a normal release, not a draft or pre-release):
     dist/${INSTALLER}  dist/${INSTALLER}.blockmap  dist/latest.yml
   For example:
     gh release create v${VERSION} dist/${INSTALLER} dist/${INSTALLER}.blockmap dist/latest.yml --repo shox17/DubEval --title "DubEval ${VERSION}" --notes-file dist/release-notes.md
   Before that, you can test the update from the last release: python tools/release_qa/release_qa.py --installer dist/${INSTALLER}\n`);
}

const command = process.argv[2];
if (command === "build") build();
else if (command === "finish") finish().catch(e => fail(e.stack || String(e)));
else fail("Usage: node scripts/release-windows.js build | finish [signed installer] [--allow-no-timestamp]");
