import autoprefixer from "autoprefixer";
import esbuild from "esbuild";
import fs from "node:fs/promises";
import path from "node:path";
import postcss from "postcss";
import tailwindcss from "tailwindcss";

const root = process.cwd();
const dist = path.join(root, "dist");
const assets = path.join(dist, "assets");
const publicDir = path.join(root, "public");

async function copyDir(source, target) {
  try {
    const entries = await fs.readdir(source, { withFileTypes: true });
    await fs.mkdir(target, { recursive: true });
    await Promise.all(
      entries.map(async (entry) => {
        const from = path.join(source, entry.name);
        const to = path.join(target, entry.name);
        if (entry.isDirectory()) {
          await copyDir(from, to);
        } else {
          await fs.copyFile(from, to);
        }
      })
    );
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
}

await fs.rm(dist, { recursive: true, force: true });
await fs.mkdir(assets, { recursive: true });

const cssInput = await fs.readFile(path.join(root, "src", "styles", "index.css"), "utf-8");
const cssResult = await postcss([tailwindcss, autoprefixer]).process(cssInput, {
  from: path.join(root, "src", "styles", "index.css"),
  to: path.join(assets, "index.css"),
});

const entry = `
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./src/App.jsx";
ReactDOM.createRoot(document.getElementById("root")).render(
  React.createElement(React.StrictMode, null, React.createElement(App))
);
`;

await esbuild.build({
  stdin: {
    contents: entry,
    resolveDir: root,
    loader: "jsx",
  },
  bundle: true,
  format: "esm",
  minify: true,
  sourcemap: false,
  outfile: path.join(assets, "index.js"),
  loader: {
    ".png": "file",
    ".jpg": "file",
    ".jpeg": "file",
    ".svg": "file",
  },
  assetNames: "assets/[name]-[hash]",
  define: {
    "import.meta.env.VITE_API_BASE_URL": "undefined",
    "import.meta.env.VITE_MAP_PROVIDER": "\"leaflet\"",
    "import.meta.env.VITE_KAKAO_JAVASCRIPT_KEY": "undefined",
  },
});

let bundledCss = "";
try {
  bundledCss = await fs.readFile(path.join(assets, "index.css"), "utf-8");
} catch {
  bundledCss = "";
}
await fs.writeFile(path.join(assets, "index.css"), `${bundledCss}\n${cssResult.css}`);

await copyDir(publicDir, dist);
await fs.writeFile(
  path.join(dist, "index.html"),
  `<!doctype html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>오늘 뭐 먹지 AI</title>
    <link rel="stylesheet" href="/assets/index.css" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/assets/index.js"></script>
  </body>
</html>
`
);

console.log("Frontend build completed: dist/");
