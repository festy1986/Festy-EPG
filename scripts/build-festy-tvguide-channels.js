const fs = require("fs");

const upstreamPath = "channels/tvguide.upstream.channels.xml";
const rawPath = "guides/tvguide.channels.xml";

const outPath = "channels/tvguide.festy.channels.xml";
const reportsDir = "reports";

fs.mkdirSync("channels", { recursive: true });
fs.mkdirSync(reportsDir, { recursive: true });

const masterList = [
  "COMET","LAFF","FOX BOSTON","FOX PORTLAND","NBC BOSTON","NBC PORTLAND",
  "ABC BOSTON","ABC PORTLAND","NEW ENGLAND CABLE NEWS","PBS","CW BOSTON",
  "CBS BOSTON","CBS PORTLAND","ION BOSTON","METV","INSP","FETV","GRIT",
  "GAME SHOW NETWORK","HEROES & ICONS","TCM","OWN","BET","DISCOVERY CHANNEL",
  "FREEFORM","USA NETWORK","NESN","NBC SPORTS BOSTON","NESN PLUS","ESPN",
  "ESPN 2 HD","WE","OXYGEN","DISNEY CHANNEL","CARTOON NETWORK","NICKELODEON",
  "MSNBC","CNN","HLN","CNBC","FOX NEWS","ION PLUS","TNT","LIFETIME","LMN",
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
  "GREAT AMERICAN FAMILY","HBO","CINEMAX","SHOWTIME","STARZ","MGM",
  "SCREENPIX","SONY MOVIES","SCREAMBOX"
];

function norm(s) {
  return String(s || "")
    .toUpperCase()
    .replace(/&AMP;/g, "&")
    .replace(/\+/g, " PLUS")
    .replace(/\bHD\b/g, "")
    .replace(/[^\w\s&]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function extractChannels(xml) {
  const blocks = [];

  for (const m of xml.matchAll(/<channel\b[\s\S]*?<\/channel>/gi)) {
    blocks.push(m[0]);
  }

  for (const m of xml.matchAll(/<channel\b[^>]*\/>/gi)) {
    blocks.push(m[0]);
  }

  return blocks;
}

function getAttr(block, attr) {
  const m = block.match(new RegExp(`${attr}="([^"]*)"`, "i"));
  return m ? m[1] : "";
}

function getName(block) {
  const display = block.match(/<display-name[^>]*>([\s\S]*?)<\/display-name>/i);
  if (display) return display[1].replace(/<[^>]+>/g, "").trim();

  return (
    getAttr(block, "xmltv_id") ||
    getAttr(block, "name") ||
    getAttr(block, "site_id") ||
    ""
  );
}

function readIfExists(path) {
  return fs.existsSync(path) ? fs.readFileSync(path, "utf8") : "";
}

const upstreamChannels = extractChannels(readIfExists(upstreamPath));
const rawChannels = extractChannels(readIfExists(rawPath));

const allChannels = [...upstreamChannels, ...rawChannels];

console.log(`Upstream channels parsed: ${upstreamChannels.length}`);
console.log(`Raw local channels parsed: ${rawChannels.length}`);

const matched = [];
const matchedNames = [];
const missing = [];

function add(block, reason) {
  const key = getAttr(block, "site_id") + "|" + getAttr(block, "xmltv_id") + "|" + getName(block);
  if (matched.some(existing => {
    const existingKey = getAttr(existing, "site_id") + "|" + getAttr(existing, "xmltv_id") + "|" + getName(existing);
    return existingKey === key;
  })) return;

  matched.push(block);
  matchedNames.push(`${getName(block)}  ← ${reason}`);
}

function findMatch(wantedName) {
  const wanted = norm(wantedName);

  return allChannels.find(block => {
    const name = norm(getName(block));
    const xmltv = norm(getAttr(block, "xmltv_id"));
    const site = norm(getAttr(block, "site_id"));

    return (
      name === wanted ||
      xmltv === wanted ||
      name.includes(wanted) ||
      xmltv.includes(wanted) ||
      site.includes(wanted)
    );
  });
}

for (const wanted of masterList) {
  const hit = findMatch(wanted);
  if (hit) add(hit, `master list: ${wanted}`);
  else missing.push(wanted);
}

const premiumKeywords = [
  "HBO", "CINEMAX", "MAX", "SHOWTIME", "PARAMOUNT PLUS WITH SHOWTIME",
  "STARZ", "ENCORE", "MGM", "SCREENPIX", "MOVIEPLEX", "MOVIE PLEX",
  "RETROPLEX", "RETRO PLEX", "INDIEPLEX", "INDIE PLEX",
  "THE MOVIE CHANNEL", "FLIX", "SONY MOVIES", "SCREAMBOX"
];

const otaKeywords = [
  "WGME", "WCSH", "WMTW", "WPFO",
  "METV", "ME TV", "COZI", "ANTENNA", "GRIT", "LAFF", "COMET",
  "ION", "COURT", "AWE", "THIS TV", "BUZZR", "DECADES", "CATCHY",
  "DABL", "CHARGE", "QUEST", "DEFY", "TRUE CRIME", "GET TV", "GETTV",
  "START TV", "HEROES", "H&I", "BOUNCE", "SCRIPPS"
];

for (const block of allChannels) {
  const haystack = norm([
    getName(block),
    getAttr(block, "xmltv_id"),
    getAttr(block, "site_id")
  ].join(" "));

  if (premiumKeywords.some(k => haystack.includes(norm(k)))) {
    add(block, "premium sweep");
  }

  if (otaKeywords.some(k => haystack.includes(norm(k)))) {
    add(block, "OTA/local sweep");
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
fs.writeFileSync(`${reportsDir}/tvguide.matched.txt`, matchedNames.join("\n") + "\n");
fs.writeFileSync(`${reportsDir}/tvguide.missing.txt`, missing.join("\n") + "\n");

console.log(`Matched: ${matched.length}`);
console.log(`Missing from master list only: ${missing.length}`);
