const fs = require('fs')

const NEW_RAW_FILE = 'guides/tvguide.xml'
const OLD_CURATED_FILE = 'guides/festy.channels.xml'
const OUTPUT_FILE = 'guides/festy.channels.xml'

function read(file) {
  if (!fs.existsSync(file)) {
    console.error(`Missing file: ${file}`)
    process.exit(1)
  }
  return fs.readFileSync(file, 'utf8')
}

function escAttr(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function norm(value) {
  return String(value || '')
    .toUpperCase()
    .replace(/&AMP;/g, '&')
    .replace(/\bHD\b/g, '')
    .replace(/\bSD\b/g, '')
    .replace(/[^A-Z0-9]+/g, '')
}

function parseChannels(xml) {
  const out = []
  const re = /<channel\b([^>]*)>([\s\S]*?)<\/channel>/g
  let m

  while ((m = re.exec(xml))) {
    const attrs = m[1]
    const name = m[2].trim()

    const get = attr => {
      const x = attrs.match(new RegExp(`${attr}="([^"]*)"`, 'i'))
      return x ? x[1] : ''
    }

    out.push({
      full: m[0],
      attrs,
      name,
      site_id: get('site_id'),
      xmltv_id: get('xmltv_id'),
      logo: get('logo'),
      lang: get('lang') || 'en',
      site: get('site') || 'tvguide.com'
    })
  }

  return out
}

const aliases = {
  COMET: ['COMET', 'WPFO-DT3'],
  LAFF: ['LAFF', 'WMTW-DT3'],
  FOXPORTLAND: ['WPFO', 'WPFO-DT'],
  NBCPORTLAND: ['WCSH', 'WCSH-DT'],
  ABCPORTLAND: ['WMTW', 'WMTW-DT'],
  CBSPORTLAND: ['WGME', 'WGME-DT'],
  NEWENGLANDCABLENEWS: ['NECN'],
  METV: ['WMTW-DT2'],
  INSP: ['INSP', 'INSPHD'],
  FETV: ['FETV'],
  GRIT: ['GRIT'],
  GAMESHOWNETWORK: ['GSNHD', 'GSN'],
  HEROESICONS: ['H&I', 'H&amp;I'],
  TCM: ['TCMHD', 'TCM'],
  OWN: ['OWNHD', 'OWN'],
  BET: ['BETHD', 'BET'],
  DISCOVERYCHANNEL: ['TDC-HD', 'TDC-E'],
  FREEFORM: ['FREEFRMHD', 'FREEFRM'],
  USANETWORK: ['USAHD', 'USA-E'],
  NESN: ['NESNHD', 'NESN'],
  NBCSPORTSBOSTON: ['NBCBOSHD', 'NBCBOS'],
  NESNPLUS: ['NESNPLUSHD'],
  ESPN: ['ESPNHD', 'ESPN'],
  ESPN2HD: ['ESPN2D', 'ESPN2'],
  WE: ['WE-HD', 'WE'],
  OXYGEN: ['OXYGENHD', 'OXGN-E'],
  DISNEYCHANNEL: ['DISNEYHD', 'DIS-E'],
  CARTOONNETWORK: ['TOONHD', 'TOON-E'],
  NICKELODEON: ['NICKHD', 'NIC-E'],
  MSNBC: ['MSNOW', 'MSNBCHD'],
  MSNOWNOW: ['MSNOW', 'MSNBCHD'],
  CNN: ['CNNHD', 'CNN'],
  HLN: ['HLNHD', 'HLN'],
  CNBC: ['CNBCHD', 'CNBC'],
  FOXNEWS: ['FNCHD', 'FOXNEW'],
  TNT: ['TNTHD', 'TNT'],
  LIFETIME: ['LIFEHD', 'LIF-E'],
  LMN: ['LMNHD', 'LMN'],
  TLC: ['TLCHD', 'TLC'],
  AMC: ['AMCHD', 'AMCALL'],
  HGTV: ['HGTVHD', 'HGTV'],
  TRAVELCHANNEL: ['TRAVELHD', 'TRAVEL'],
  AE: ['A&E-HD', 'A&amp;E-HD', 'A&E', 'A&amp;E'],
  FOODNETWORK: ['FOODHD', 'FOODTV'],
  BRAVO: ['BRAVOHD', 'BRAVO'],
  TRUTV: ['TRUTVHD', 'TRUTV'],
  NATIONALGEOGRAPHIC: ['NGCHD', 'NGC-E'],
  HALLMARKCHANNEL: ['HALLMARKHD', 'HALMRK'],
  SYFY: ['SyFyHD', 'SyFy'],
  ANIMALPLANET: ['ANIMALHD', 'ANIMAL'],
  HISTORYCHANNEL: ['THCHD', 'THC'],
  THEWEATHERCHANNEL: ['WEATHHD', 'WEATH'],
  PARAMOUNTNETWORK: ['PARMT', 'SPIKEHD'],
  COMEDYCENTRAL: ['COMEDYHD', 'CMDY-E'],
  FX: ['FXHD', 'FX-E'],
  FXX: ['FXXHD'],
  EENTERTAINMENT: ['ETV-HD', 'ETV-E'],
  FXM: ['FXMHD', 'FXM'],
  AXS: ['AXSTV'],
  TVLAND: ['TVLANDHD', 'TVLAND'],
  TBS: ['TBSHD', 'TBS'],
  VH1: ['VH1HD', 'VH-1E'],
  MTV: ['MTVHD', 'MTV-E'],
  CMT: ['CMTHD', 'CMTV'],
  DESTINATIONAMERICA: ['DESTAMERHD', 'DESTAMER'],
  MAGNOLIA: ['MAGNHD', 'MAGN'],
  DISCOVERYLIFE: ['DLIF'],
  NATGEOWILD: ['NGEOWILDHD', 'NGEOWILD'],
  SMITHSONIANCHANNEL: ['SMITHSONHD'],
  BBCAMERICA: ['BBCAMHD', 'BBCAME'],
  HALLMARKMYSTERY: ['HMMHD', 'HALLMYS'],
  HALLMARKDRAMA: ['HALLDRMHD'],
  POP: ['POPHD', 'POP'],
  CRIMEANDINVESTIGATION: ['CRIMEINVHD'],
  VICE: ['VICEHD'],
  INVESTIGATIONDISCOVERY: ['INVSTDSCHD', 'ID'],
  REELZ: ['REELZHD'],
  DISCOVERYFAMILY: ['DFCHHD'],
  DISCOVERYSCIENCE: ['SCIENCEHD', 'SCIENCE'],
  AMERICANHEROESCHANNEL: ['AHCHD', 'AHC'],
  FUSE: ['FUSEHD'],
  MTV2: ['MTV2HD'],
  IFC: ['IFCHD'],
  FYI: ['FYIHD'],
  COOKINGCHANNEL: ['COOKINGHD'],
  LOGO: ['LOGO'],
  FOXSPORTS2: ['FS2'],
  FOXSPORTS1: ['FS1HD', 'FS1'],
  NFLNETWORK: ['NFLHD', 'NFLNET'],
  NHLNETWORK: ['NHLTVHD'],
  MLBNETWORK: ['MLBHD'],
  NBATV: ['NBAHD'],
  CBSSPORTSNETWORK: ['CBSSPTHD'],
  ESPNNEWS: ['ESPNNEWHD'],
  OVATION: ['OVATHD'],
  UPTV: ['UPTVHD'],
  OUTDOORCHANNEL: ['OUTHDE'],
  ASPIRE: ['ASPIRE'],
  GREATAMERICANFAMILY: ['GACFAM']
}

const rawXml = read(NEW_RAW_FILE)
const curatedXml = read(OLD_CURATED_FILE)

const raw = parseChannels(rawXml)
const curated = parseChannels(curatedXml)

const rawByNorm = new Map()

for (const ch of raw) {
  const keys = [
    norm(ch.name),
    norm(ch.xmltv_id.replace(/\.us$/i, ''))
  ]

  for (const key of keys) {
    if (!key) continue
    if (!rawByNorm.has(key)) rawByNorm.set(key, ch)
  }
}

function findNewChannel(old) {
  const oldNameNorm = norm(old.name)

  const possible = [
    oldNameNorm,
    oldNameNorm.replace(/NETWORK/g, ''),
    oldNameNorm.replace(/CHANNEL/g, ''),
    oldNameNorm.replace(/HD/g, '')
  ]

  if (aliases[oldNameNorm]) {
    possible.unshift(...aliases[oldNameNorm].map(norm))
  }

  for (const key of possible) {
    if (rawByNorm.has(key)) return rawByNorm.get(key)
  }

  for (const [aliasKey, values] of Object.entries(aliases)) {
    if (oldNameNorm.includes(aliasKey) || aliasKey.includes(oldNameNorm)) {
      for (const value of values) {
        const key = norm(value)
        if (rawByNorm.has(key)) return rawByNorm.get(key)
      }
    }
  }

  return null
}

let updated = 0
let unchanged = 0
let missing = []

let output = `<?xml version="1.0" encoding="UTF-8"?>\n<site site="tvguide.com">\n`

for (const old of curated) {
  const found = findNewChannel(old)

  let siteId = old.site_id

  if (found) {
    siteId = found.site_id
    updated++
  } else {
    unchanged++
    missing.push(old.name)
  }

  const attrs = [
    `site="tvguide.com"`,
    `site_id="${escAttr(siteId)}"`,
    `lang="${escAttr(old.lang)}"`,
    `xmltv_id="${escAttr(old.xmltv_id)}"`
  ]

  if (old.logo) attrs.push(`logo="${escAttr(old.logo)}"`)

  output += `<channel ${attrs.join(' ')}>${old.name}</channel>\n`
}

output += `</site>\n`

fs.writeFileSync(OUTPUT_FILE, output)

console.log(`Updated IDs: ${updated}`)
console.log(`Left unchanged: ${unchanged}`)

if (missing.length) {
  console.log('\nCould not confidently match:')
  for (const name of missing) console.log(`- ${name}`)
}
