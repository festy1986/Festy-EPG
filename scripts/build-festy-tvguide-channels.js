const fs = require("fs");

const upstreamPath = "channels/tvguide.upstream.channels.xml";
const rawPath = "guides/tvguide.channels.xml";
const outPath = "channels/tvguide.festy.channels.xml";
const reportsDir = "reports";

fs.mkdirSync("channels", { recursive: true });
fs.mkdirSync(reportsDir, { recursive: true });

const skipMaster = new Set([
  "FOX BOSTON",
  "NBC BOSTON",
  "ABC BOSTON",
  "CBS BOSTON",
  "CW BOSTON",
  "ION BOSTON"
]);

const masterList = [
  "COMET","LAFF","FOX PORTLAND","NBC PORTLAND","ABC PORTLAND",
  "NEW ENGLAND CABLE NEWS","PBS","CBS PORTLAND","METV","INSP","FETV","GRIT",
  "GAME SHOW NETWORK","HEROES & ICONS","TCM","OWN","BET","DISCOVERY CHANNEL",
  "FREEFORM","USA NETWORK","NESN","NBC SPORTS BOSTON","NESN PLUS","ESPN",
  "ESPN 2 HD","WE","OXYGEN","DISNEY CHANNEL","CARTOON NETWORK","NICKELODEON",
  "MS NOW","CNN","HLN","CNBC","FOX NEWS","ION PLUS","TNT","LIFETIME","LMN",
  "TLC","AMC","HGTV","TRAVEL CHANNEL","A&E","FOOD NETWORK","BRAVO","TRU TV",
  "NAT GEO MUNDO","HALLMARK CHANNEL","SYFY","ANIMAL PLANET","HISTORY CHANNEL",
  "THE WEATHER CHANNEL","PARAMOUNT NETWORK","COMEDY CENTRAL","FX","FXX",
  "E! ENTERTAINMENT","FXM","AXS","TV LAND","TBS","VH1","MTV","CMT",
  "DESTINATION AMERICA","MAGNOLIA","DISCOVERY LIFE","NAT GEO WILD",
  "SMITHSONIAN CHANNEL","BBC AMERICA","HALLMARK MYSTERY","HALLMARK DRAMA",
  "POP","CRIME AND INVESTIGATION","VICE","INVESTIGATION DISCOVERY","REELZ",
  "DISCOVERY FAMILY","DISCOVERY SCIENCE","AMERICAN HEROES CHANNEL","AMC PLUS",
  "FUSE","MTV 2","IFC","ADULT SWIM","FYI","COOKING CHANNEL","LOGO","COURT TV",
  "ANTENNA TV","ION MYSTERY","FOX SPORTS 2","FOX SPORTS 1","NFL NETWORK",
  "NHL NETWORK","MLB NETWORK","NBA TV","CBS SPORTS NETWORK","CBS SPORTS HQ",
  "ESPN NEWS","OVATION","UP TV","COZI TV","OUTDOOR CHANNEL","ASPIRE","AWE",
  "GREAT AMERICAN FAMILY"
];

const exactAliases = {
  "FOX PORTLAND": ["WPFO"],
  "NBC PORTLAND": ["WCSH"],
  "ABC PORTLAND": ["WMTW"],
  "CBS PORTLAND": ["WGME"],

  "MS NOW": ["MSNBC", "MS NOW", "MSNOW"],
  "ESPN 2 HD": ["ESPN2", "ESPN 2"],
  "ESPN NEWS": ["ESPNEWS", "ESPN NEWS"],
  "WE": ["WETV", "WE TV"],
  "BET": ["BET"],
  "MTV": ["MTV"],
  "MTV 2": ["MTV2", "MTV 2"],
  "FXM": ["FXMOVIECHANNEL", "FX MOVIE CHANNEL"],
  "TRU TV": ["TRUTV", "TRU TV"],
  "A&E": ["A&E", "A AND E"],
  "E! ENTERTAINMENT": ["E", "E ENTERTAINMENT"],
  "NAT GEO WILD": ["NATIONAL GEOGRAPHIC WILD", "NAT GEO WILD"],
  "NAT GEO MUNDO": ["NAT GEO MUNDO", "NATIONAL GEOGRAPHIC MUNDO"],
  "HALLMARK MYSTERY": ["HALLMARK MYSTERY", "HALLMARK MOVIES MYSTERIES"],
  "CRIME AND INVESTIGATION": ["CRIME PLUS INVESTIGATION", "CRIME INVESTIGATION"],
  "INVESTIGATION DISCOVERY": ["INVESTIGATION DISCOVERY"],
  "AMERICAN HEROES CHANNEL": ["AMERICAN HEROES CHANNEL"],
  "AMC PLUS": ["AMC PLUS", "AMC+"],
  "ION PLUS": ["ION PLUS"],
  "ION MYSTERY": ["ION MYSTERY"],
  "COZI TV": ["COZI", "COZI TV"],
  "METV": ["METV", "ME TV"],
  "HEROES & ICONS": ["HEROES ICONS", "H&I"],
  "GAME SHOW NETWORK": ["GAME SHOW NETWORK", "GSN"]
};

const premiumKeywords = [
  "HBO", "CINEMAX", "MAX",
  "SHOWTIME", "PARAMOUNT PLUS WITH SHOWTIME",
  "STARZ", "ENCORE",
  "MGM", "MGM PLUS",
  "SCREENPIX",
  "MOVIEPLEX", "MOVIE PLEX",
  "RETROPLEX", "RETRO PLEX",
  "INDIEPLEX", "INDIE PLEX",
  "THE MOVIE CHANNEL",
  "FLIX",
  "SONY MOVIES",
  "SCREAMBOX"
];

const portlandCallSigns = [
  "WGME",
  "WCSH",
  "WMTW",
  "WPFO",
  "WMEA",
  "WPXT",
  "WPME"
];

function norm(s) {
  return String(s || "")
    .toUpperCase()
    .replace(/&AMP;/g, "&")
    .replace(/&/g, " AND ")
    .replace(/\+/g, " PLUS ")
    .replace(/\bHD\b/g, "")
    .replace(/\bSD\b/g, "")
    .replace(/[^\w\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function compact(s) {
  return norm(s).replace(/\s+/g, "");
}

function readIfExists(path) {
  return fs.existsSync(path) ? fs.readFileSync(path, "utf8") : "";
}

function extractChannels(xml) {
  const blocks = [];
  for (const m of xml.matchAll(/<channel\b[\s\S]*?<\/channel>/gi)) blocks.push(m[0]);
  for (const m of xml.matchAll(/<channel\b[^>]*\/>/gi)) blocks.push(m[0]);
  return blocks;
}

function getAttr(block, attr) {
  const m = block.match(new RegExp(`${attr}="([^"]*)"`, "i"));
  return m ? m[1] : "";
}

function getName(block) {
  const display = block.match(/<display-name[^>]*>([\s\S]*?)<\/display-name>/i);
  if (display) return display[1].replace(/<[^>]+>/g, "").trim();

  return getAttr(block, "xmltv_id") || getAttr(block, "name") || getAttr(block, "site_id") || "";
}

function haystack(block) {
  return [
    getName(block),
    getAttr(block, "xmltv_id"),
    getAttr(block, "site_id")
  ].join(" ");
}

const upstreamChannels = extractChannels(readIfExists(upstreamPath));
const rawChannels = extractChannels(readIfExists(rawPath));
const allChannels = [...upstreamChannels, ...rawChannels];

console.log(`Upstream channels parsed: ${upstreamChannels.length}`);
console.log(`Raw local channels parsed: ${rawChannels.length}`);

const matched = [];
const matchedKeys = new Set();
const matchedReport = [];
const missing = [];

function keyFor(block) {
  return `${getAttr(block, "site_id")}|${getAttr(block, "xmltv_id")}|${getName(block)}`;
}

function add(block, reason) {
  const key = keyFor(block);
  if (matchedKeys.has(key)) return;

  matchedKeys.add(key);
  matched.push(block);
  matchedReport.push(`${getName(block)}  ← ${reason}`);
}

function exactMatch(name) {
  const aliases = [name, ...(exactAliases[name] || [])];
  const aliasNorms = aliases.map(norm);
  const aliasCompacts = aliases.map(compact);

  return allChannels.find(block => {
    const fields = [
      getName(block),
      getAttr(block, "xmltv_id"),
      getAttr(block, "name")
    ];

    return fields.some(field => {
      const n = norm(field);
      const c = compact(field);
      return aliasNorms.includes(n) || aliasCompacts.includes(c);
    });
  });
}

for (const wanted of masterList) {
  if (skipMaster.has(wanted)) continue;

  const hit = exactMatch(wanted);
  if (hit) add(hit, `master list: ${wanted}`);
  else missing.push(wanted);
}

for (const block of allChannels) {
  const h = norm(haystack(block));

  if (premiumKeywords.some(k => h.includes(norm(k)))) {
    add(block, "premium movie sweep");
  }
}

for (const block of rawChannels) {
  const h = norm(haystack(block));

  if (portlandCallSigns.some(call => h.includes(call))) {
    add(block, "Portland OTA call-sign sweep");
  }
}

const output = [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<site site="tvguide.com">',
  ...matched,
  '</site>',
  ''
].join("\n");

fs.writeFileSync(outPath, output);
fs.writeFileSync(`${reportsDir}/tvguide.matched.txt`, matchedReport.join("\n") + "\n");
fs.writeFileSync(`${reportsDir}/tvguide.missing.txt`, missing.join("\n") + "\n");

console.log(`Matched: ${matched.length}`);
console.log(`Missing from master list only: ${missing.length}`);
