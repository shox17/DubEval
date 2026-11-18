// electron-builder afterPack hook, run before the app is signed.
// Windows: stamps DubEval's icon, name and version into DubEval.exe with rcedit. electron-builder's own step for this is
// off (signAndEditExecutable: false) because its signing tools need symlinks, which Windows only allows in Developer
// Mode. The icon is build/icon.ico (see NOTICE).
// macOS: signs every program and library of the bundled Python with the app's Developer ID, the hardened runtime and a
// secure timestamp, which Apple's notarization requires of each one inside the app. electron-builder's own signing skips
// the bundled Python and models (build.mac.signIgnore): it would sign each of their thousands of data files, and a
// read-only model stopped it. It then signs Electron and seals the whole app, these files included. An ad-hoc build
// (identity "-", npm run dist:mac:adhoc) leaves them with their makers' signatures, as before.
const { execFile } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const { promisify } = require("node:util");

const run = promisify(execFile);
const SIGN_AT_ONCE = 8;
const MACHO_THIN = [Buffer.from([0xcf, 0xfa, 0xed, 0xfe]), Buffer.from([0xce, 0xfa, 0xed, 0xfe])];
const MACHO_FAT = Buffer.from([0xca, 0xfe, 0xba, 0xbe]);
const MH_EXECUTE = 2;

// "program" (a Mach-O executable), "library" (any other Mach-O file) or null, from how the file starts.
function machO(file) {
  const fd = fs.openSync(file, "r");
  try {
    const head = Buffer.alloc(32);
    if (fs.readSync(fd, head, 0, 32, 0) < 16) return null;
    let at = 0;
    if (head.subarray(0, 4).equals(MACHO_FAT)) {
      // A universal file: its first part's header says what it is. Java class files start the same way, with a
      // version number of 45 or more where a universal file counts its parts.
      if (head.readUInt32BE(4) >= 45) return null;
      at = head.readUInt32BE(16);
      if (fs.readSync(fd, head, 0, 16, at) < 16) return null;
    }
    if (!MACHO_THIN.some(magic => head.subarray(0, 4).equals(magic))) return null;
    return head.readUInt32LE(12) === MH_EXECUTE ? "program" : "library";
  } finally {
    fs.closeSync(fd);
  }
}

function* machOFiles(folder) {
  for (const entry of fs.readdirSync(folder, { withFileTypes: true })) {
    const file = path.join(folder, entry.name);
    if (entry.isDirectory()) yield* machOFiles(file);
    else if (entry.isFile()) {
      const kind = machO(file);
      if (kind) yield { file, kind };
    }
  }
}

async function signBundledPython(context) {
  const mac = context.packager.platformSpecificBuildOptions;
  if (!mac.identity || mac.identity === "-") return;
  const identity = mac.identity.startsWith("Developer ID Application:") ? mac.identity
    : `Developer ID Application: ${mac.identity}`;
  const entitlements = path.join(__dirname, mac.entitlements);
  const resources = path.join(context.appOutDir, `${context.packager.appInfo.productFilename}.app`, "Contents",
    "Resources");
  const files = [];
  for (const folder of ["python", "models"]) {
    const root = path.join(resources, folder);
    if (fs.existsSync(root)) files.push(...machOFiles(root));
  }
  console.log(`  • signing ${files.length} programs and libraries of the bundled Python  identity=${identity}`);
  const sign = ({ file, kind }) => run("codesign", ["--force", "--timestamp", "--options", "runtime",
    ...(kind === "program" ? ["--entitlements", entitlements] : []), "--sign", identity, file]);
  // The first alone: macOS may ask once for permission to use the key (Always Allow), and eight boxes at once failed.
  if (files.length) await sign(files[0]);
  for (let i = 1; i < files.length; i += SIGN_AT_ONCE) {
    await Promise.all(files.slice(i, i + SIGN_AT_ONCE).map(sign));
  }
}

async function stampWindowsExe(context) {
  const rcedit = require("rcedit");
  const { productFilename, info } = context.packager.appInfo;
  const exe = path.join(context.appOutDir, `${productFilename}.exe`);
  const icon = path.join(__dirname, "build", "icon.ico");
  const version = info._metadata.version;
  await rcedit(exe, {
    ...(fs.existsSync(icon) ? { icon } : {}),
    "file-version": version,
    "product-version": version,
    "version-string": {
      ProductName: "DubEval",
      FileDescription: "DubEval",
      CompanyName: "DubEval contributors",
      OriginalFilename: `${productFilename}.exe`,
      LegalCopyright: "AGPL-3.0-or-later",
    },
  });
}

exports.default = async function afterPack(context) {
  if (context.electronPlatformName === "win32") await stampWindowsExe(context);
  else if (context.electronPlatformName === "darwin") await signBundledPython(context);
};
exports.machO = machO;
