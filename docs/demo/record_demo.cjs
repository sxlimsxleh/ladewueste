// Renders the Ladewüste demo video frame by frame with Playwright, then ffmpeg assembles it.
//
// Why frame by frame: in a headless browser without a GPU, WebGL renders slowly and grabbing one
// frame takes seconds, so a plain screen recording stutters. Here the script moves the camera itself,
// one step per captured frame, and takes each frame from Chrome's screencast stream (about twice as
// fast as a screenshot). Still moments are captured once and held; UI animations become clean cuts.
//
// Usage (the demo build must be served, e.g. `VITE_DEMO=1 npx vite --port 5174` in web/):
//   node docs/demo/record_demo.cjs http://localhost:5174/ <frames dir>
//   then docs/demo/make_video.sh <frames dir>
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const [URL = "http://localhost:5174/", OUT = "frames"] = process.argv.slice(2);
const CAMERA_FPS = 15; // captured frames per second during camera moves (ffmpeg outputs 30 fps)
const VIEW = { width: 1280, height: 720 }; // 720p video

fs.mkdirSync(OUT, { recursive: true });
const concat = []; // ffmpeg concat entries: [file, seconds]
let n = 0;

(async () => {
  const browser = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  const page = await browser.newPage({ viewport: VIEW });
  const wait = (ms) => page.waitForTimeout(ms);

  // Frames come from Chrome's screencast: every drawn frame arrives as a JPEG.
  const cdp = await page.context().newCDPSession(page);
  let latest = null;
  let waiting = [];
  cdp.on("Page.screencastFrame", async (frame) => {
    latest = frame.data;
    waiting.splice(0).forEach((resolve) => resolve());
    await cdp.send("Page.screencastFrameAck", { sessionId: frame.sessionId }).catch(() => {});
  });
  /** The next drawn frame, or the last one if nothing changes on screen within `ms`. */
  const nextFrame = (ms = 4000) => new Promise((resolve) => { waiting.push(resolve); setTimeout(resolve, ms); });

  async function shot(seconds, { fresh = true } = {}) {
    if (fresh || !latest) await nextFrame();
    const file = `f${String(++n).padStart(5, "0")}.jpg`;
    fs.writeFileSync(path.join(OUT, file), Buffer.from(latest, "base64"));
    concat.push([file, seconds]);
    if (n % 20 === 0) console.log(`frame ${n}`);
  }
  /** Wait until the map has finished loading tiles and drawing (or give up after `ms`). */
  const settle = (ms = 8000) =>
    page.evaluate((ms) => new Promise((res) => {
      const map = window.__ladewuesteMap;
      if (map.loaded() && !map.isMoving()) return setTimeout(res, 250);
      const t = setTimeout(res, ms);
      map.once("idle", () => { clearTimeout(t); setTimeout(res, 150); });
    }), ms);
  async function hold(seconds) { await settle(); await shot(seconds); }
  /** Eased camera move, one jumpTo + screenshot per output frame. */
  async function camera(to, seconds) {
    const from = await page.evaluate(() => {
      const m = window.__ladewuesteMap; const c = m.getCenter();
      return { lng: c.lng, lat: c.lat, zoom: m.getZoom(), pitch: m.getPitch(), bearing: m.getBearing() };
    });
    const frames = Math.round(seconds * CAMERA_FPS);
    for (let i = 1; i <= frames; i++) {
      const t = i / frames; const e = t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2; // easeInOutCubic
      const at = Object.fromEntries(Object.keys(from).map((k) => [k, from[k] + (to[k] - from[k]) * e]));
      const frame = nextFrame();
      await page.evaluate((at) => window.__ladewuesteMap.jumpTo({ center: [at.lng, at.lat], zoom: at.zoom, pitch: at.pitch, bearing: at.bearing }), at);
      await frame;
      await shot(1 / CAMERA_FPS, { fresh: false });
    }
  }

  // Overlays drawn into the page: captions, title/end cards, a visible cursor with a click ripple.
  async function overlay() {
    await page.addStyleTag({ content: `
      #demo-caption{position:fixed;left:50%;bottom:58px;transform:translateX(-50%);z-index:9999;max-width:880px;
        padding:12px 22px;border-radius:14px;background:rgba(8,11,16,.88);border:1px solid rgba(232,190,120,.35);
        color:#e6edf3;font:600 21px/1.35 ui-sans-serif,system-ui,sans-serif;text-align:center;box-shadow:0 10px 40px rgba(0,0,0,.5)}
      #demo-caption b{color:#e8be78}
      #demo-card{position:fixed;inset:0;z-index:10000;display:flex;flex-direction:column;align-items:center;justify-content:center;
        background:radial-gradient(ellipse at center,#141b24 0%,#0b0f14 70%);color:#e6edf3;font-family:ui-sans-serif,system-ui,sans-serif;text-align:center}
      #demo-card h1{font-size:64px;margin:0;letter-spacing:-1px} #demo-card h1 span{color:#e8be78}
      #demo-card p{font-size:24px;color:#8b98a8;margin:14px 0 0} #demo-card .small{font-size:16px;margin-top:36px}
      #demo-cursor{position:fixed;z-index:10001;width:22px;height:22px;pointer-events:none;transition:left .45s ease,top .45s ease;
        filter:drop-shadow(0 1px 2px rgba(0,0,0,.8))}
      #demo-ripple{position:fixed;z-index:10000;width:14px;height:14px;margin:-7px 0 0 -7px;border-radius:50%;border:2px solid #fff;
        pointer-events:none;opacity:0}
      #demo-ripple.go{animation:ripple .6s ease-out}
      @keyframes ripple{from{opacity:1;transform:scale(1)}to{opacity:0;transform:scale(4)}}` });
    await page.evaluate(() => {
      const cursor = document.createElement("div"); cursor.id = "demo-cursor"; cursor.style.left = "-50px";
      cursor.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22"><path d="M3 2l7 19 2.5-7.5L20 11z" fill="#fff" stroke="#0b0f14" stroke-width="1.2"/></svg>';
      const ripple = document.createElement("div"); ripple.id = "demo-ripple";
      document.body.append(cursor, ripple);
    });
  }
  const caption = (html) => page.evaluate((html) => {
    let el = document.getElementById("demo-caption");
    if (!html) { el?.remove(); return; }
    if (!el) { el = document.createElement("div"); el.id = "demo-caption"; document.body.append(el); }
    el.innerHTML = html;
  }, html);
  const card = (html) => page.evaluate((html) => {
    let el = document.getElementById("demo-card");
    if (!html) { el?.remove(); return; }
    if (!el) { el = document.createElement("div"); el.id = "demo-card"; document.body.append(el); }
    el.innerHTML = html;
  }, html);
  async function click(x, y) {
    await page.evaluate(([x, y]) => { const c = document.getElementById("demo-cursor"); c.style.left = x + "px"; c.style.top = y + "px"; }, [x, y]);
    await wait(600);
    await shot(0.4); // cursor in place, just before the click
    await page.mouse.move(x - 4, y - 4); await page.mouse.move(x, y, { steps: 3 }); await wait(150);
    await page.mouse.click(x, y);
    await page.evaluate(([x, y]) => { const r = document.getElementById("demo-ripple"); r.style.left = x + "px"; r.style.top = y + "px"; r.classList.remove("go"); void r.offsetWidth; r.classList.add("go"); }, [x, y]);
  }
  const project = (lng, lat) => page.evaluate(([lng, lat]) => { const p = window.__ladewuesteMap.project([lng, lat]); return [p.x, p.y]; }, [lng, lat]);
  const sitesShown = () => page.evaluate(() => Number(document.querySelector('[role="radio"][value="algorithm"]')?.textContent.match(/\((\d+)\)/)?.[1] ?? 0));

  // ------------------------------------------------------------------ the film
  await page.goto(URL, { waitUntil: "load" });
  await cdp.send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: VIEW.width, maxHeight: VIEW.height });
  await overlay();
  await card(`<h1>Ladew<span>ü</span>ste</h1><p>Where does Germany run out of fast chargers?</p>
    <p class="small">116,443 charging stations · Bundesnetzagentur register · cleaned, mapped, and turned into a game</p>`);
  await wait(9000);
  await shot(3.5);
  await card(null);
  await page.evaluate(() => window.__ladewuesteMap.jumpTo({ center: [10.3, 51.1], zoom: 5.0, pitch: 30, bearing: -20 }));
  await settle();

  await caption("Germany in 10,959 hexagons. Height = fast-charging power.");
  await camera({ lng: 10.45, lat: 51.2, zoom: 5.35, pitch: 50, bearing: -4 }, 4.5);
  await hold(1.5);

  await caption("<b>Sand</b> = more than 25 km from a fast-charging hub: <b>19,318 km²</b>, 5.4% of Germany.");
  await camera({ lng: 11.6, lat: 52.55, zoom: 6.4, pitch: 48, bearing: -10 }, 4);
  await hold(2.2);

  await caption("This cell has 8 fast chargers. But no real <b>hub</b> (6+ chargers at one site) within 25 km.");
  const [cx, cy] = await project(11.126, 52.983);
  await click(cx, cy);
  await wait(1200);
  await hold(4.2);
  await page.keyboard.press("Escape");

  await caption("Play mode: drop your own hubs. Every desert cell they reach turns green.");
  await page.mouse.click(640, 712); await page.keyboard.press("p");
  await wait(1500);
  await hold(1.2);
  for (const [lng, lat] of [[13.25, 51.72], [11.15, 52.78], [13.3, 53.1]]) {
    const [x, y] = await project(lng, lat);
    await click(x, y);
    await wait(1500); // ring grows, cells turn green, counter counts down
    await hold(1.3);
  }
  await hold(0.8);

  await caption("…then race the <b>greedy algorithm</b>: same rules, same number of sites.");
  const [ax, ay] = await page.evaluate(() => {
    const b = [...document.querySelectorAll("button")].find((el) => el.textContent.includes("Auto-plan")).getBoundingClientRect();
    return [b.x + b.width / 2, b.y + b.height / 2];
  });
  await click(ax, ay);
  // Stop-motion: one frame per algorithm site as it drops in.
  let shown = 0; const start = Date.now();
  while (shown < 10 && Date.now() - start < 90000) {
    const now = await sitesShown();
    if (now > shown) { shown = now; await wait(500); await shot(0.6, { fresh: false }); }
    else await wait(100);
  }
  await wait(1500);
  await caption("You vs the algorithm, scored live. Browser and Python agree to the km².");
  await page.getByRole("radio", { name: /Your plan/ }).click();
  await wait(1200);
  await hold(4.0);

  await caption("Data Doctor: every fix to the raw register, counted. 13 rules, 55 dbt tests, nothing silently dropped.");
  await page.evaluate(() => { document.getElementById("demo-cursor").style.left = "-50px"; });
  await page.getByRole("link", { name: "Data Doctor" }).click();
  await wait(2500);
  await shot(3.2);
  const scroller = 'div.overflow-y-auto';
  for (let i = 1; i <= 20; i++) {
    await page.evaluate(([sel, y]) => document.querySelector(sel).scrollTo(0, y), [scroller, Math.round(820 * (1 - Math.cos((Math.PI * i) / 20)) / 2)]);
    await shot(1 / 15);
  }
  await caption("Example: 196 stations from 19 cities, all placed at one point in the North Sea. Flagged, not guessed.");
  await page.evaluate((sel) => { const el = document.querySelector("#rule-R10"); const box = document.querySelector(sel); box.scrollTo(0, el.offsetTop - 70); }, scroller);
  await wait(400);
  await shot(3.8);
  await caption(null);

  await card(`<h1>Ladew<span>ü</span>ste</h1><p>Try it: <b style="color:#e6edf3">sxlimsxleh.github.io/ladewueste</b></p>
    <p>Code: github.com/sxlimsxleh/ladewueste</p>
    <p class="small">Data: Bundesnetzagentur.de, Ladesäulenregister (CC BY 4.0), as of 01.09.2026 · Map © OpenStreetMap contributors, OpenFreeMap</p>`);
  await shot(4.5);

  // ffmpeg concat list (the last file is repeated, as the concat demuxer requires).
  const list = concat.map(([f, d]) => `file '${f}'\nduration ${d.toFixed(4)}`).join("\n") + `\nfile '${concat.at(-1)[0]}'\n`;
  fs.writeFileSync(path.join(OUT, "frames.txt"), list);
  const total = concat.reduce((s, [, d]) => s + d, 0);
  console.log(`${n} frames, ${total.toFixed(1)} s of video`);
  await browser.close();
})();
