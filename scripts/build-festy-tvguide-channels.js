const fs = require("fs");

const upstreamPath = "channels/tvguide.upstream.channels.xml";
const rawPath = "guides/tvguide.channels.xml";
const outPath = "channels/tvguide.festy.channels.xml";
const reportsDir = "reports";

fs.mkdirSync("channels", { recursive: true });
fs.mkdirSync(reportsDir, { recursive: true });

const masterList = [
  "COMET","LAFF","FOX PORTLAND","NBC PORTLAND","ABC PORTLAND",
  "NEW ENGLAND CABLE NEWS","PBS","CBS PORTLAND","METV","INSP","FETV","GRIT",
  "GAME SHOW NETWORK","HEROES & ICONS","TCM","OWN","BET","DISCOVERY CHANNEL",
  "FREEFORM","USA NETWORK","NESN","NBC SPORTS BOSTON","NESN PLUS","ESPN",
  "ESPN 2 HD","WE","OXYGEN","DISNEY CHANNEL","CARTOON NETWORK","NICKELODEON",
  "MS NOW","CNN","HLN","CNBC","FOX NEWS","ION PLUS","TNT","LIFETIME","LMN",
  "TLC","AMC","HGTV","TRAVEL CHANNEL","A&E","FOOD NETWORK","BRAVO","TRU TV",
  "NATIONAL GEOGRAPHIC","HALLMARK CHANNEL","SYFY","ANIMAL PLANET","HISTORY",
  "THE WEATHER CHANNEL","PARAMOUNT NETWORK","COMEDY CENTRAL","FX","FXX",
  "E! ENTERTAINMENT","FXM","AXS","TV LAND","TBS","VH1","MTV","CMT",
  "DESTINATION AMERICA","MAGNOLIA","DISCOVERY LIFE","NAT GEO WILD",
  "SMITHSONIAN CHANNEL","BBC AMERICA","HALLMARK MYSTERY","HALLMARK DRAMA",
  "POP","CRIME AND INVESTIGATION","VICE","INVESTIGATION DISCOVERY","REELZ",
  "DISCOVERY FAMILY","SCIENCE","AMERICAN HEROES CHANNEL","AMC PLUS",
  "FUSE","MTV 2","IFC","ADULT SWIM","FYI","COOKING CHANNEL","LOGO","COURT TV",
  "ANTENNA TV","ION MYSTERY","FOX SPORTS 2","FOX SPORTS 1","NFL NETWORK",
  "NHL NETWORK","MLB NETWORK","NBA TV","CBS SPORTS NETWORK","ESPN NEWS",
  "OVATION","UP TV","COZI TV","OUTDOOR CHANNEL","ASPIRE","AWE",
  "GREAT AMERICAN FAMILY"
];

const aliases = {
  "FOX PORTLAND": ["WPFO", "FOX 23", "WPFO FOX"],
  "NBC PORTLAND": ["WCSH", "NEWS CENTER MAINE", "NBC 6"],
  "ABC PORTLAND": ["WMTW", "ABC 8"],
  "CBS PORTLAND": ["WGME", "CBS 13"],

  "NEW ENGLAND CABLE NEWS": ["NECN"],
  "MS NOW": ["MSNBC", "MS NOW", "MSNOW"],

  "NATIONAL GEOGRAPHIC": ["NATIONAL GEOGRAPHIC", "NAT GEO", "NATIONALGEOGRAPHIC"],
  "HISTORY": ["HISTORY", "HISTORY CHANNEL"],
  "SCIENCE": ["SCIENCE", "SCIENCE CHANNEL", "DISCOVERY SCIENCE"],
  "NESN": ["NESN", "NEW ENGLAND SPORTS NETWORK"],
  "NESN PLUS": ["NESN PLUS", "NESN+", "NEW ENGLAND SPORTS NETWORK PLUS"],
  "NBC SPORTS BOSTON": ["NBC SPORTS BOSTON", "BOSTON SPORTS", "NBCSB"],

  "A&E": ["A&E", "AETV", "A AND E"],
  "LMN": ["LMN", "LIFETIME MOVIE NETWORK"],
  "UP TV": ["UP", "UPTV", "UP TV"],
  "AWE": ["AWE", "A WEALTH OF ENTERTAINMENT"],
  "ASPIRE": ["ASPIRE", "ASPIRETV"],

  "METV": ["METV", "ME TV"],
  "COZI TV": ["COZI", "COZI TV"],
  "ION PLUS": ["ION PLUS", "IONPLUS"],
  "ION MYSTERY": ["ION MYSTERY", "IONMYSTERY"],
  "ANTENNA TV": ["ANTENNA TV", "ANTENNATV"],
  "COURT TV": ["COURT TV", "COURTTV"],
  "HEROES & ICONS": ["HEROES & ICONS", "HEROES AND ICONS", "H&I"],
  "GAME SHOW NETWORK": ["GAME SHOW NETWORK", "GSN"],

  "ESPN 2 HD": ["ESPN2", "ESPN 2"],
  "ESPN NEWS": ["ESPNEWS", "ESPN NEWS"],
  "WE": ["WETV", "WE TV"],
  "TRU TV": ["TRUTV", "TRU TV"],
  "E! ENTERTAINMENT": ["E!", "E ENTERTAINMENT"],
  "FXM": ["FX MOVIE CHANNEL", "FXMOVIECHANNEL"],
  "NAT GEO WILD": ["NATIONAL GEOGRAPHIC WILD", "NAT GEO WILD"],
  "HALLMARK MYSTERY": ["HALLMARK MYSTERY", "HALLMARK MOVIES MYSTERIES"],
  "CRIME AND INVESTIGATION": ["CRIME PLUS INVESTIGATION", "CRIME INVESTIGATION"],
  "INVESTIGATION DISCOVERY": ["INVESTIGATION DISCOVERY"],
  "AMERICAN HEROES CHANNEL": ["AMERICAN HEROES CHANNEL"],
  "AMC PLUS": ["AMC PLUS", "AMC+"],
  "MTV 2": ["MTV2", "MTV 2"]
};

const rejectContains = {
  "BET": ["BETHER"],
  "MTV": ["MTV2", "MTVLIVE", "MTVCLASSIC"],
  "HBO": ["HBOFAMILY", "HBOCOMEDY", "HBOZONE", "HBOSIGNATURE", "HBO2"],
  "SHOWTIME": ["SHOWTIMEFAMILYZONE", "SHOWTIMEWOMEN", "SHOWTIMENEXT", "SHOWTIMEEXTREME", "SHOWTIME2", "SHOWTIMESHOWCASE"],
  "STARZ": ["STARZENCORE", "STARZEDGE", "STARZCOMEDY", "STARZCINEMA", "STARZKIDSFAMILY", "STARZINBLACK"],
  "MGM": ["MGMPLUSDRIVEIN", "MGMPLUSMARQUEE", "MGMPLUSHITS", "MGMPLUSHORROR"]
};

const premiumKeywords = [
  "HBO","CINEMAX","ACTIONMAX","THRILLERMAX","MOVIEMAX","MOREMAX","OUTERMAX","5STARMAX",
  "SHOWTIME","PARAMOUNT PLUS WITH SHOWTIME","STARZ","ENCORE","MGM","MGM PLUS",
  "SCREENPIX","MOVIEPLEX","RETROPLEX","INDIEPLEX","THE MOVIE CHANNEL","FLIX",
  "SONY MOVIES","SCREAMBOX"
];

const portlandCallSigns = [
  "WGME","WCSH","WMTW","WPFO","WMEA","WPXT","WPME","WCBB"
];

function norm(s) {
  return String(s || "")
    .toUpperCase()
    .replace(/&AMP;/g, "&")
    .replace(/&/g, " AND ")
    .replace(/\+/g, " PLUS ")
    .replace(/\bHD\b/g, "")
    .replace(/\bSD\b/g, "")
    .replace(/\.US\b/g, "")
    .replace(/@EAST/g, "")
    .replace(/@WEST/g, "")
    .replace(/[^\w\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function compact(s) {
  return norm(s).replace(/\s+/g, "");
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

  const inner = block.match(/<channel\b[^>]*>([\s\S]*?)<\/channel>/i);
  if (inner) return inner[1].replace(/<[^>]+>/g, "").trim();

  return getAttr(block, "xmltv_id") || getAttr(block, "name") || getAttr(block, "site_id") || "";
}

function haystack(block) {
  return [
    getName(block),
    getAttr(block, "xmltv_id"),
    getAttr(block, "name"),
    getAttr(block, "site_id")
  ].join(" ");
}

const upstreamChannels = extractChannels(fs.readFileSync(upstreamPath, "utf8"));
const rawChannels = extractChannels(fs.readFileSync(rawPath, "utf8"));

// RAW FIRST now — locals/subchannels come from your Portland dump.
const allChannels = [...rawChannels, ...upstreamChannels];

console.log(`Upstream channels parsed: ${upstreamChannels.length}`);
console.log(`Raw local channels parsed: ${rawChannels.length}`);

const matched = [];
const matchedKeys = new Set();
const matchedReport = [];
const missing = [];

function add(block, reason) {
  const key = `${getAttr(block, "site_id")}|${getAttr(block, "xmltv_id")}|${getName(block)}`;
  if (matchedKeys.has(key)) return;

  matchedKeys.add(key);
  matched.push(block);
  matchedReport.push(`${getName(block)}  ← ${reason}`);
}

function isRejected(wanted, block) {
  const bad = rejectContains[wanted] || [];
  const c = compact(haystack(block));
  return bad.some(x => c.includes(compact(x)));
}

function findBest(wanted) {
  const terms = [wanted, ...(aliases[wanted] || [])].map(compact);

  const candidates = allChannels.filter(block => {
    if (isRejected(wanted, block)) return false;

    const h = compact(haystack(block));

    return terms.some(t =>
      h === t ||
      h.startsWith(t) ||
      h.includes(t)
    );
  });

  if (!candidates.length) return null;

  candidates.sort((a, b) => {
    const aName = compact(getName(a));
    const bName = compact(getName(b));
    const wantedMain = compact(wanted);

    const aExact = aName === wantedMain ? 0 : 1;
    const bExact = bName === wantedMain ? 0 : 1;

    return aExact - bExact || aName.length - bName.length;
  });

  return candidates[0];
}

for (const wanted of masterList) {
  const hit = findBest(wanted);
  if (hit) add(hit, `master list: ${wanted}`);
  else missing.push(wanted);
}

// Premium sweep from both raw + upstream.
for (const block of allChannels) {
  const h = norm(haystack(block));
  if (premiumKeywords.some(k => h.includes(norm(k)))) {
    add(block, "premium movie sweep");
  }
}

// Portland OTA sweep from raw local lineup only.
for (const block of rawChannels) {
  const h = norm(haystack(block));
  if (portlandCallSigns.some(call => h.includes(call))) {
    add(block, "Portland OTA call-sign sweep");
  }
}

fs.writeFileSync(outPath, [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<site site="tvguide.com">',
  ...matched,
  '</site>',
  ''
].join("\n"));

fs.writeFileSync(`${reportsDir}/tvguide.matched.txt`, matchedReport.join("\n") + "\n");
fs.writeFileSync(`${reportsDir}/tvguide.missing.txt`, missing.join("\n") + "\n");

console.log(`Matched: ${matched.length}`);
console.log(`Missing from master list only: ${missing.length}`);
