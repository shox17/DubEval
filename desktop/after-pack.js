// electron-builder afterPack hook: stamps DubEval's icon, name and version into DubEval.exe with rcedit.
// electron-builder's own step for this is off (signAndEditExecutable: false) because its signing tools need symlinks,
// which Windows only allows in Developer Mode. The icon is build/icon.ico (see NOTICE).
const fs = require("node:fs");
const path = require("node:path");
const rcedit = require("rcedit");

exports.default = async function afterPack(context) {
  if (context.electronPlatformName !== "win32") return;
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
};
