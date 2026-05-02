const fs = require("fs");
const path = require("path");

const repo = process.env.GITHUB_REPOSITORY || "festy1986/festy-epg";
const branch = process.env.GITHUB_REF_NAME || "main";

const logoDir = "logos";

const possibleChannelFiles = [
  "guides/tvguide.channels.xml",
  "sites/tvguide.com/tvguide.channels.xml",
  "sites/tvguide.com/festy.channels.xml",
  "festy.channels.xml"
];

const channelFile = possibleChannelFiles.find(f => fs.existsSync(f));

if (!channelFile) {
  console.error("Could not find your personal channel XML file.");
  process.exit(1);
}

if (!fs.existsSync(logoDir)) {
  console.error("Missing logos folder.");
  process.exit(1);
}

function decodeXml(s) {
  return s
    .replace(/&amp;/g, "&")
    .replace(/&apos;/g, "'")
    .replace(/&quot;/g, '"');
}

function normalize(s) {
  return decodeXml(s)
    .toLowerCase()
    .replace(/\.(png|jpg|jpeg|webp|svg)$/i, "")
    .replace(/\bhd\b/g, "")
    .replace(/\bsd\b/g, "")
    .replace(/\beast\b/g, "")
    .replace(/\bwest\b/g, "")
    .replace(/\(.*?\)/g, "")
    .replace(/&/g, "and")
    .replace(/\+/g, "plus")
    .replace(/[^a-z0-9]+/g, "")
    .trim();
}

function rawLogoUrl(filename) {
  return `https://raw.githubusercontent.com/${repo}/${branch}/logos/${encodeURIComponent(filename)}`;
}

const logos = fs.readdirSync(logoDir)
  .filter(f => /\.(png|jpg|jpeg|webp|svg)$/i.test(f));

const logoMap = new Map();

for (const logo of logos) {
  logoMap.set(normalize(logo), logo);
}

const aliases = {
  "msnow": "MS NOW HD",
  "msnbc": "MS NOW HD",
  "usanetwork": "usa network",
  "usa": "usa network",
  "aande": "A&E",
  "ae": "A&E",
  "heroesandicons": "Heroes & Icons Network",
  "hi": "Heroes & Icons Network",
  "metv": "MeTV",
  "newenglandsportsnetwork": "New England Sports Network",
  "nesn": "New England Sports Network",
  "newenglandsportsnetworkplus": "New England Sports Network Plus HD",
  "nesnplus": "New England Sports Network Plus HD",
  "lifetimemovienetwork": "lifetime movie network",
  "lmn": "lifetime movie network",
  "fxmovie": "FX Movie HD",
  "fxm": "FX Movie HD",
  "theweatherchannel": "The Weather",
  "weatherchannel": "The Weather",
  "sciencechannel": "Science HD",
  "science": "Science HD",
  "discoverychannel": "discovery",
  "nationalgeographic": "National Geographic",
  "natgeo": "National Geographic",
  "nationalgeographicwild": "National Geographic Wild",
  "natgeowild": "National Geographic Wild",
  "up": "Up Entertainment HD",
  "uptv": "Up Entertainment HD",
  "greatamericanfamily": "Great American Family",
  "gaf": "Great American Family",
  "hallmarkchannel": "Hallmark",
  "hallmarkmystery": "Hallmark Mystery HD",
  "hallmarkdrama": "Hallmark Family",
  "hallmarkfamily": "Hallmark Family",
  "paramountnetwork": "Paramount Network HD",
  "comedycentral": "Comedy Central",
  "cartoonnetwork": "Cartoon Network",
  "foodnetwork": "Food Network HD",
  "gameshownetwork": "Game Show Network HD",
  "cbssportsnetwork": "CBS Sports Network HD",
  "espnnews": "ESPN News HD",
  "nhlnetwork": "NHL Network HD",
  "mlbnetwork": "MLB Network HD",
  "nbatv": "NBA TV HD",
  "foxsports1": "FOX Sports 1 HD",
  "fs1": "FOX Sports 1 HD",
  "foxsports2": "FOX Sports 2",
  "fs2": "FOX Sports 2"
};

let xml = fs.readFileSync(channelFile, "utf8");

let matched = 0;
let missed = 0;

xml = xml.replace(
  /<channel([^>]*)>([\s\S]*?)<\/channel>/g,
  (full, attrs, name) => {
    const cleanName = decodeXml(name.trim());
    const key = normalize(cleanName);

    let logoFile = logoMap.get(key);

    if (!logoFile && aliases[key]) {
      logoFile = logoMap.get(normalize(aliases[key]));
    }

    if (!logoFile) {
      for (const [logoKey, file] of logoMap.entries()) {
        if (logoKey && (logoKey.includes(key) || key.includes(logoKey))) {
          logoFile = file;
          break;
        }
      }
    }

    if (!logoFile) {
      console.log(`NO LOGO MATCH: ${cleanName}`);
      missed++;
      return full.replace(/\slogo="[^"]*"/, "");
    }

    const logoUrl = rawLogoUrl(logoFile);
    matched++;

    let newAttrs = attrs.replace(/\slogo="[^"]*"/, "");
    newAttrs += ` logo="${logoUrl}"`;

    console.log(`MATCHED: ${cleanName} -> ${logoFile}`);

    return `<channel${newAttrs}>${name}</channel>`;
  }
);

fs.writeFileSync(channelFile, xml);

console.log("");
console.log(`Updated channel file: ${channelFile}`);
console.log(`Matched logos: ${matched}`);
console.log(`No logo match: ${missed}`);
