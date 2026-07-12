import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const distDir = path.join(__dirname, "frontend", "dist");
const indexFile = path.join(distDir, "index.html");
const port = Number(process.env.PUBLIC_DEMO_PORT || 8088);
const backendPort = Number(process.env.BACKEND_PORT || 8000);

const mimeTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".png", "image/png"],
  [".jpg", "image/jpeg"],
  [".jpeg", "image/jpeg"],
  [".webp", "image/webp"],
  [".ico", "image/x-icon"],
  [".woff", "font/woff"],
  [".woff2", "font/woff2"],
]);

function sendText(res, statusCode, body) {
  res.writeHead(statusCode, { "content-type": "text/plain; charset=utf-8" });
  res.end(body);
}

function proxyApi(req, res) {
  const headers = { ...req.headers, host: `127.0.0.1:${backendPort}` };
  const upstream = http.request(
    {
      hostname: "127.0.0.1",
      port: backendPort,
      path: req.url,
      method: req.method,
      headers,
    },
    (upstreamRes) => {
      res.writeHead(upstreamRes.statusCode || 502, upstreamRes.headers);
      upstreamRes.pipe(res);
    },
  );

  upstream.on("error", () => {
    sendText(res, 502, "后端接口暂时不可用，请确认 backend 服务正在运行。");
  });

  req.pipe(upstream);
}

function serveFile(req, res, filePath, isFallback = false) {
  const extension = path.extname(filePath).toLowerCase();
  const contentType = mimeTypes.get(extension) || "application/octet-stream";
  const cacheControl = isFallback
    ? "no-cache"
    : filePath.includes(`${path.sep}assets${path.sep}`)
      ? "public, max-age=31536000, immutable"
      : "no-cache";

  res.writeHead(200, {
    "content-type": contentType,
    "cache-control": cacheControl,
  });

  if (req.method === "HEAD") {
    res.end();
    return;
  }

  fs.createReadStream(filePath).pipe(res);
}

const server = http.createServer((req, res) => {
  if (!req.url) {
    sendText(res, 400, "Bad Request");
    return;
  }

  const url = new URL(req.url, `http://${req.headers.host || "127.0.0.1"}`);

  if (url.pathname.startsWith("/api/")) {
    proxyApi(req, res);
    return;
  }

  if (!["GET", "HEAD"].includes(req.method || "")) {
    sendText(res, 405, "Method Not Allowed");
    return;
  }

  let decodedPath = "/";
  try {
    decodedPath = decodeURIComponent(url.pathname);
  } catch {
    sendText(res, 400, "Bad Request");
    return;
  }

  const requestedPath = path.resolve(
    distDir,
    decodedPath === "/" ? "index.html" : `.${decodedPath}`,
  );

  if (!requestedPath.startsWith(distDir)) {
    sendText(res, 403, "Forbidden");
    return;
  }

  fs.stat(requestedPath, (error, stat) => {
    if (!error && stat.isFile()) {
      serveFile(req, res, requestedPath);
      return;
    }

    fs.stat(indexFile, (indexError) => {
      if (indexError) {
        sendText(res, 500, "前端生产文件不存在，请先运行 npm run build。");
        return;
      }

      serveFile(req, res, indexFile, true);
    });
  });
});

server.listen(port, "127.0.0.1", () => {
  console.log(`Public demo server listening at http://127.0.0.1:${port}`);
  console.log(`Proxying /api/* to http://127.0.0.1:${backendPort}`);
});
