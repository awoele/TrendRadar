const fs = require("fs");
const path = require("path");

const bundledNodeModules =
  "C:\\Users\\Administrator\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\node_modules";
process.env.NODE_PATH = [
  process.env.NODE_PATH,
  bundledNodeModules,
  path.join(bundledNodeModules, ".pnpm", "node_modules"),
]
  .filter(Boolean)
  .join(path.delimiter);
require("module").Module._initPaths();

const { chromium } = require("playwright");

const SOURCE_NAME = "douyin:favorites";
const START_URL = "https://www.douyin.com/user/self";
const MY_FAVORITES_TEXT = "\u6211\u7684\u6536\u85cf";
const FAVORITES_TEXT = "\u6536\u85cf";
const TODAY = new Date().toISOString().slice(0, 10);
const STANDARD_COLUMNS = [
  "platform",
  "title",
  "url",
  "cover_url",
  "author",
  "published_at",
  "like_count",
  "comment_count",
  "collect_count",
  "share_count",
  "description",
  "source",
];

const args = parseArgs(process.argv.slice(2));
const repoRoot = path.resolve(__dirname, "..");
const sharedProfile = "D:\\Documents\\agents\\.auth\\platform-profile";
const repoProfile = path.resolve(repoRoot, ".auth/platform-profile");
const profileDir = path.resolve(args.profile || (fs.existsSync(sharedProfile) ? sharedProfile : repoProfile));
const outPath = path.resolve(repoRoot, args.out || `data/imports/04_douyin_favorites_${TODAY}.csv`);
const maxRows = Number(args.max || 300);
const scrolls = Number(args.scrolls || 18);
const waitMs = Number(args["wait-ms"] || 1800);
const headless = Boolean(args.headless);

main().catch((error) => {
  console.error(error && error.stack ? error.stack : error);
  process.exit(1);
});

async function main() {
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.mkdirSync(profileDir, { recursive: true });

  const context = await chromium.launchPersistentContext(profileDir, {
    headless,
    viewport: { width: 1360, height: 900 },
    locale: "zh-CN",
    args: ["--disable-blink-features=AutomationControlled"],
  });

  const apiRowsByUrl = new Map();
  let lastHasMore = true;
  let lastCursor = "";

  try {
    const page = context.pages()[0] || (await context.newPage());
    page.on("response", async (response) => {
      const url = response.url();
      if (!/\/aweme\/v1\/web\/aweme\/listcollection\//.test(url)) return;
      try {
        const payload = await response.json();
        lastHasMore = Boolean(payload.has_more);
        lastCursor = String(payload.cursor || payload.max_cursor || "");
        for (const item of payload.aweme_list || []) {
          const row = rowFromAweme(item);
          if (row.url && !apiRowsByUrl.has(row.url)) {
            apiRowsByUrl.set(row.url, row);
          }
        }
      } catch (error) {
        console.warn(`Could not parse Douyin collection response: ${error.message}`);
      }
    });

    await openFavoritesCollection(page);

    if (args["login-only"]) {
      console.log(`Login profile kept at ${profileDir}`);
      return;
    }

    const blocked = await detectBlock(page);
    if (blocked) {
      throw new Error(blocked);
    }

    const menuTarget = await clickMyFavoritesEntry(page);
    await page.waitForTimeout(waitMs * 2);

    let idleRounds = 0;
    let previousCount = apiRowsByUrl.size;
    await moveMouseIntoFavoritesPane(page, menuTarget);
    for (let index = 0; index < scrolls && apiRowsByUrl.size < maxRows; index += 1) {
      await page.mouse.wheel(0, 1100).catch(() => {});
      await page.waitForTimeout(waitMs);
      if (apiRowsByUrl.size === previousCount) {
        idleRounds += 1;
      } else {
        idleRounds = 0;
        previousCount = apiRowsByUrl.size;
      }
      if (!lastHasMore && idleRounds >= 2) {
        break;
      }
      if (idleRounds >= 5) {
        break;
      }
    }

    let rows = Array.from(apiRowsByUrl.values()).slice(0, maxRows);
    if (!rows.length) {
      rows = await collectPreviewRowsFromDom(page);
    }
    writeCsv(rows, outPath);

    const status = await readFavoriteStatus(page);
    console.log(`Douyin favorites collected: ${rows.length}`);
    if (status) {
      console.log(`Page status: ${status}`);
    }
    if (lastCursor) {
      console.log(`Last cursor: ${lastCursor}; has_more=${lastHasMore ? "1" : "0"}`);
    }
    console.log(`CSV: ${outPath}`);
  } finally {
    await context.close();
  }
}

async function openFavoritesCollection(page) {
  await page.goto(START_URL, { waitUntil: "domcontentloaded", timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(waitMs * 2);
  const viewport = page.viewportSize() || { width: 1360, height: 900 };
  await page.mouse.click(viewport.width - 34, 28).catch(() => {});
  await page.waitForTimeout(waitMs);
}

async function clickMyFavoritesEntry(page) {
  const target = await page.evaluate((myFavoritesText) => {
    const candidates = Array.from(document.querySelectorAll("button, a, div, span"))
      .map((element) => {
        const rect = element.getBoundingClientRect();
        const text = (element.innerText || element.textContent || "").trim().replace(/\s+/g, " ");
        return {
          text,
          x: rect.left + rect.width / 2,
          y: rect.top + rect.height / 2,
          width: rect.width,
          height: rect.height,
          top: rect.top,
          left: rect.left,
        };
      })
      .filter((item) => {
        if (!item.text || !item.width || !item.height) return false;
        if (!item.text.includes(myFavoritesText)) return false;
        return item.top > 150 && item.top < 420 && item.left > window.innerWidth * 0.55;
      })
      .sort((a, b) => a.width - b.width || a.top - b.top);
    return candidates[0] || null;
  }, MY_FAVORITES_TEXT);

  if (!target) {
    throw new Error("Could not find the Douyin account menu favorites entry.");
  }
  await page.mouse.click(target.x, target.y).catch(() => {});
  return target;
}

async function moveMouseIntoFavoritesPane(page, target) {
  const viewport = page.viewportSize() || { width: 1360, height: 900 };
  const x = Math.min(viewport.width - 120, Math.max(viewport.width * 0.76, target?.x || viewport.width - 180));
  const y = Math.min(viewport.height - 120, Math.max(300, (target?.y || 250) + 130));
  await page.mouse.move(x, y).catch(() => {});
}

function rowFromAweme(item) {
  const stats = item.statistics || {};
  const awemeId = String(item.aweme_id || item.awemeId || item.id || "").trim();
  const desc = clean(item.desc || item.caption || "");
  return {
    platform: "douyin",
    title: (desc || `Douyin ${awemeId}`).slice(0, 160),
    url: awemeId ? `https://www.douyin.com/video/${awemeId}` : "",
    cover_url: coverFromAweme(item),
    author: clean(item.author?.nickname || item.author?.unique_id || ""),
    published_at: dateFromUnix(item.create_time),
    like_count: countValue(stats.digg_count),
    comment_count: countValue(stats.comment_count),
    collect_count: countValue(stats.collect_count),
    share_count: countValue(stats.share_count),
    description: desc.slice(0, 600),
    source: SOURCE_NAME,
  };
}

function coverFromAweme(item) {
  const candidates = [
    item.video?.cover?.url_list,
    item.video?.origin_cover?.url_list,
    item.video?.dynamic_cover?.url_list,
    item.images?.[0]?.url_list,
    item.images?.[0]?.download_url_list,
  ];
  for (const value of candidates) {
    const first = Array.isArray(value) ? value.find(Boolean) : value;
    const url = normalizeImageUrl(first);
    if (url) return url;
  }
  return "";
}

async function collectPreviewRowsFromDom(page) {
  return page.evaluate((sourceName) => {
    const rows = [];
    const cards = Array.from(document.querySelectorAll("img[src*='PackSourceEnum_COLLECTION']"))
      .map((image) => image.closest("div"))
      .filter(Boolean);
    for (const card of cards) {
      const root = card.parentElement?.parentElement || card;
      const text = clean(root.innerText || "");
      const title = text.split(/\n+/).map(clean).filter(Boolean)[0] || "";
      if (!title) continue;
      const image = root.querySelector("img[src*='PackSourceEnum_COLLECTION']");
      rows.push({
        platform: "douyin",
        title: title.slice(0, 160),
        url: "",
        cover_url: image?.currentSrc || image?.src || "",
        author: "",
        published_at: "",
        like_count: "",
        comment_count: "",
        collect_count: "",
        share_count: "",
        description: text.slice(0, 600),
        source: sourceName,
      });
    }
    return rows.filter((row) => row.title && row.cover_url);

    function clean(value) {
      return String(value || "").replace(/\u200b/g, "").replace(/\s+/g, " ").trim();
    }
  }, SOURCE_NAME);
}

async function detectBlock(page) {
  return page.evaluate(() => {
    const body = document.body?.innerText || "";
    const url = location.href;
    if (/captcha|verify/i.test(url)) return "Douyin verification page is open.";
    const terms = [
      "\u5b89\u5168\u9a8c\u8bc1",
      "\u626b\u7801\u767b\u5f55",
      "\u9a8c\u8bc1\u7801",
      "\u767b\u5f55\u540e\u5373\u53ef",
    ];
    if (terms.some((term) => body.includes(term))) return "Douyin login or verification is required.";
    return "";
  });
}

async function readFavoriteStatus(page) {
  return page.evaluate(({ favoritesText, myFavoritesText }) => {
    const text = document.body?.innerText || "";
    const myMatch = text.match(new RegExp(`${myFavoritesText}\\s*([0-9]+)`));
    if (myMatch) return `${myFavoritesText} ${myMatch[1]}`;
    const match = text.match(new RegExp(`${favoritesText}\\s*([0-9]+)`));
    if (match) return `${favoritesText} ${match[1]}`;
    if (text.includes("\u6682\u65e0\u5185\u5bb9")) return "\u6682\u65e0\u5185\u5bb9";
    return "";
  }, { favoritesText: FAVORITES_TEXT, myFavoritesText: MY_FAVORITES_TEXT });
}

function writeCsv(rows, filename) {
  const lines = [STANDARD_COLUMNS.join(",")];
  for (const row of rows) {
    if (!row.url) continue;
    lines.push(STANDARD_COLUMNS.map((column) => csvEscape(row[column] || "")).join(","));
  }
  fs.writeFileSync(filename, `\ufeff${lines.join("\n")}\n`, "utf8");
}

function dateFromUnix(value) {
  const seconds = Number(value || 0);
  if (!seconds) return "";
  return new Date(seconds * 1000).toISOString().slice(0, 10);
}

function countValue(value) {
  if (value === null || value === undefined || value === "") return "";
  return String(value);
}

function normalizeImageUrl(value) {
  const text = clean(value);
  if (!text || text.startsWith("data:") || text.startsWith("blob:")) return "";
  if (text.startsWith("//")) return `https:${text}`;
  if (!/^https?:\/\//i.test(text)) return "";
  return text;
}

function clean(value) {
  return String(value || "").replace(/\u200b/g, "").replace(/\s+/g, " ").trim();
}

function csvEscape(value) {
  const text = String(value);
  if (!/[",\n\r]/.test(text)) return text;
  return `"${text.replace(/"/g, '""')}"`;
}

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) {
      parsed[key] = true;
    } else {
      parsed[key] = next;
      index += 1;
    }
  }
  return parsed;
}
