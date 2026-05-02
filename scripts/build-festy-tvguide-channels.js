const fs = require("fs");

const upstreamPath = "channels/tvguide.upstream.channels.xml";
const rawPath = "guides/tvguide.channels.xml";

const outPath = "channels/tvguide.festy.channels.xml";
const reportsDir = "reports";

if (!fs.existsSync(reportsDir)) fs.mkdirSync(reportsDir, { recursive: true });

const masterList = [
  // your full master list (unchanged, expanded later by logic)
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
  "GREAT AMERICAN FAMILY","HBO","HBO HITS","HBO 2","HBO COMEDY","HBO ZONE",
  "HBO SIGNATURE","HBO WEST","CINEMAX","CINEMAX ACTION","CINEMAX HITS",
  "CINEMAX CLASSICS","OUTERMAX","MOREMAX","SHOWTIME PARAMOUNT",
  "SHOWTIME 2","SHOWTIME BET","SHOWTIME HD","SHOWTIME EXTREME",
  "SHOWTIME FAMILY ZONE","SHOWTIME WOMEN","SHOWTIME NEXT","SHOWCASE",
  "SHOWTIME","SHOWTIME EXTREME HD","USI SHOWTIME","STARZ CINEMA","STARZ",
  "STARZ EDGE","STARZ COMEDY","STARZ ENCORE","STARZ ENCORE BLACK",
  "STARZ ENCORE CLASSIC","STARZ ENCORE FAMILY","STARZ ENCORE ACTION",
  "STARZ IN BLACK","STARZ ENCORE SUSPENSE","STARZ KIDS & FAMILY",
  "MOVIE PLEX","RETRO PLEX","INDIE PLEX","MGM","MGM MARQUEE","MGM DRIVE-IN",
  "MGM HITS","MGM HORROR","SCREENPIX","SCREENPIX ACTION","SCREENPIX VOICES",
  "SCREENPIX WESTERNS","SONY MOVIES","SCREAMBOX"
];

// --- helpers ---
function norm(s) {
  return String(s || "")
    .toUpperCase()
    .replace(/&AMP;/g, "&")
    .replace(/\+/g, " PLUS")
    .replace(/\bHD\b/g, "")
    .replace(/[^\w\s&]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function extractChannels(xml) {
  const regex = /<channel[\s\S]*?<\/channel>/g;
  return xml.match(regex) || [];
}

function getName(block) {
  const m = block.match(/<display-name[^>]*>([\s\S]*?)<\/display-name>/i);
  return m ? m[1].replace(/<[^>]+>/g, "").trim() : "";
}

// --- load sources ---
const upstreamXML = fs.existsSync(upstreamPath)
  ? fs.readFileSync(upstreamPath, "utf8")
  : "";

const rawXML = fs.readFileSync(rawPath, "utf8");

const upstreamChannels = extractChannels(upstreamXML);
const rawChannels = extractChannels(rawXML);

// --- matching ---
const matched = [];
const missing = [];

// function to find a match in a list
function findMatch(name, list) {
  const n = norm(name);
  return list.find(block => {
    const cname = norm(getName(block));
    return cname === n || cname.includes(n) || n.includes(cname);
  });
}

// --- master list matching ---
for (const ch of masterList) {
  let hit = findMatch(ch, upstreamChannels);
  if (!hit) hit = findMatch(ch, rawChannels);

  if (hit) {
    if (!matched.includes(hit)) matched.push(hit);
  } else {
    missing.push(ch);
  }
}

// --- premium sweep (auto include ALL variants) ---
const premiumKeywords = [
  "HBO","CINEMAX","SHOWTIME","STARZ","ENCORE","MGM","SCREENPIX","PLEX"
];

for (const block of rawChannels) {
  const name = norm(getName(block));
  if (premiumKeywords.some(k => name.includes(k))) {
    if (!matched.includes(block)) matched.push(block);
  }
}

// --- OTA sweep (locals + subchannels) ---
const otaKeywords = [
  "WGME","WCSH","WMTW","WPFO",
  "METV","COZI","ANTENNA","GRIT","LAFF","COMET","ION","COURT","AWE"
];

for (const block of rawChannels) {
  const name = norm(getName(block));
  if (otaKeywords.some(k => name.includes(k))) {
    if (!matched.includes(block)) matched.push(block);
  }
}

// --- output ---
const output = [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<site site="tvguide.com">',
  ...matched,
  '</site>'
].join("\n");

fs.writeFileSync(outPath, output);

// --- reports ---
fs.writeFileSync(
  `${reportsDir}/tvguide.matched.txt`,
  matched.map(b => getName(b)).join("\n")
);

fs.writeFileSync(
  `${reportsDir}/tvguide.missing.txt`,
  missing.join("\n")
);

console.log(`Matched: ${matched.length}`);
console.log(`Missing: ${missing.length}`);
