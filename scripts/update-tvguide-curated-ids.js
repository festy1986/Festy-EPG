const fs = require('fs')

const RAW_FILE = 'guides/tvguide.xml'
const CURATED_FILE = 'guides/festy.channels.xml'
const OUTPUT_FILE = 'guides/festy.channels.xml'

function read(file) {
  if (!fs.existsSync(file)) {
    console.error(`Missing file: ${file}`)
    process.exit(1)
  }
  return fs.readFileSync(file, 'utf8')
}

function getAttr(attrs, name) {
  const m = attrs.match(new RegExp(`${name}="([^"]*)"`, 'i'))
  return m ? m[1] : ''
}

function parse(xml) {
  const channels = []
  const re = /<channel\b([^>]*)>([\s\S]*?)<\/channel>/g
  let m

  while ((m = re.exec(xml))) {
    channels.push({
      full: m[0],
      attrs: m[1],
      name: m[2].trim(),
      site_id: getAttr(m[1], 'site_id'),
      xmltv_id: getAttr(m[1], 'xmltv_id'),
      logo: getAttr(m[1], 'logo'),
      lang: getAttr(m[1], 'lang') || 'en'
    })
  }

  return channels
}

function escapeAttr(v) {
  return String(v || '')
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function suffix(siteId) {
  return String(siteId || '').split('#').pop()
}

function norm(s) {
  return String(s || '')
    .toUpperCase()
    .replace(/&AMP;/g, '&')
    .replace(/&/g, 'AND')
    .replace(/\bHD\b/g, '')
    .replace(/\bSD\b/g, '')
    .replace(/[^A-Z0-9]+/g, '')
}

const raw = parse(read(RAW_FILE))
const curated = parse(read(CURATED_FILE))

const rawBySuffix = new Map()
const rawByName = new Map()

for (const ch of raw) {
  rawBySuffix.set(suffix(ch.site_id), ch)

  const keys = [
    norm(ch.name),
    norm(ch.xmltv_id.replace(/\.us$/i, ''))
  ]

  for (const key of keys) {
    if (key && !rawByName.has(key)) rawByName.set(key, ch)
  }
}

const aliases = {
  ROAR: ['WPFO'],
  NBC: ['WCSH'],
  ABC: ['WMTW'],
  CBS: ['WGME'],
  PBS: ['WCBB-DT', 'WCBB'],
  CW: ['WPXT'],
  FOX: ['WGME-DT2', 'WPFO'],
  METV: ['WMTW-DT2'],

  'ION MYSTERY': ['WPXT-DT3'],
  'THE NEST': ['WGME-DT3'],
  'TRUE CRIME NETWORK': ['WCSH-DT2'],
  QUEST: ['WCSH-DT3'],
  'PBS KIDS': ['WCBB-DT4'],
  CHARGE: ['WPFO-DT2'],

  'CRIME AND INVESTIGATION NETWORK': ['CRIMEINVHD'],
  'UP ENTERTAINMENT': ['UPTVHD'],
  'HALLMARK FAMILY': ['HALLDRMHD'],
  COURTTV: ['COURTTV'],
  GRIT: ['GRIT'],
  IONPLUS: ['IONPLUS'],
  ANTENNATV: ['ANTENNA'],
  COZITV: ['COZI'],

  HBO: ['HBOHD'],
  HBO2: ['HBO2HD'],
  HBOSIGNATURE: ['HBOSIGHD'],
  HBOCOMEDY: ['HBOCOMHD'],
  HBOZONE: ['HBOZONHD'],
  HBOLATINO: ['HBOLATHD'],
  HBOFAMILY: ['HBOFAM'],
  HBOHITS: ['HBOHITS'],
  HBOMOVIES: ['HBOMOVIES'],
  HBODRAMA: ['HBOSIGHD'],

  CINEMAX: ['MAXHD'],
  MOREMAX: ['MOREMAXHD'],
  ACTIONMAX: ['ACTMAXHD'],
  THRILLERMAX: ['THRMAX'],
  OUTERMAX: ['OUTERMAX'],
  MOVIEMAX: ['MOVIEMAX'],
  '5STARMAX': ['5STARMAXHD'],

  PARAMOUNTSHOWTIME: ['SHOHD'],
  PARAMOUNTWITHSHOWTIME: ['SHOHD'],
  SHOWTIME: ['SHOHD'],
  SHOWTIME2: ['SHO2XEHD'],
  SHOWTIMENEXT: ['SHOWNEXT'],
  SHOWTIMEWOMEN: ['SHOWWOM'],
  SHOWTIMEFAMILYZONE: ['SHOWFAM'],
  SHOWTIMEEXTREME: ['SHOWEXHD'],
  SHOWTIMESHOWCASE: ['SHWCASEHD'],

  STARZ: ['STARZHD'],
  STARZEDGE: ['STARZEDHD'],
  STARZCINEMA: ['STARZCINHD'],
  STARZCOMEDY: ['STARZCOMHD'],
  STARZENCORE: ['ENCOREHD'],
  STARZENCOREACTION: ['ENCRACTHD'],
  STARZENCOREBLACK: ['ENCRBLHD'],
  STARZENCORECLASSIC: ['ENCRCLHD'],
  STARZENCOREFAMILY: ['ENCORFM'],
  STARZENCORESUSPENSE: ['ENCORSHD'],
  STARZKIDSANDFAMILY: ['STARZFAMHD'],
  STARZINBLACK: ['STARZBLKHD'],

  MGM: ['MGM+'],
  MGMPLUS: ['MGM+'],
  MGMHITS: ['MGM+HIT'],
  MGMPLUSHits: ['MGM+HIT'],
  MGMMARQUEE: ['MGM+MAR'],
  MGMPLUSMARQUEE: ['MGM+MAR'],
  MGMDRIVEIN: ['MGM+DRV'],
  MGMPLUSDRIVEIN: ['MGM+DRV'],

  MOVIEPLEX: ['PLEXHD'],
  ENCOREMOVIEPLEX: ['PLEXHD'],
  INDIEPLEX: ['INDIPX'],
  RETROPLEX: ['RETRPLEXHD'],
  FLIX: ['FLIX-E']
}

let updatedBySuffix = 0
let updatedByName = 0
let unchanged = []
let out = `<?xml version="1.0" encoding="UTF-8"?>\n<site site="tvguide.com">\n`

for (const old of curated) {
  let found = null

  const oldSuffix = suffix(old.site_id)

  if (rawBySuffix.has(oldSuffix)) {
    found = rawBySuffix.get(oldSuffix)
    updatedBySuffix++
  } else {
    const cleanOldName = norm(old.name)
    const keys = [cleanOldName]

    for (const [alias, rawNames] of Object.entries(aliases)) {
      if (cleanOldName.includes(norm(alias))) {
        keys.push(...rawNames.map(norm))
      }
    }

    for (const key of keys) {
      if (rawByName.has(key)) {
        found = rawByName.get(key)
        updatedByName++
        break
      }
    }
  }

  const newSiteId = found ? found.site_id : old.site_id

  if (!found) unchanged.push(old.name)

  const attrs = [
    `site="tvguide.com"`,
    `site_id="${escapeAttr(newSiteId)}"`,
    `lang="${escapeAttr(old.lang)}"`,
    `xmltv_id="${escapeAttr(old.xmltv_id)}"`
  ]

  if (old.logo) attrs.push(`logo="${escapeAttr(old.logo)}"`)

  out += `<channel ${attrs.join(' ')}>${old.name}</channel>\n`
}

out += `</site>\n`

fs.writeFileSync(OUTPUT_FILE, out)

console.log(`Updated by old station ID suffix: ${updatedBySuffix}`)
console.log(`Updated by name fallback: ${updatedByName}`)
console.log(`Left unchanged: ${unchanged.length}`)

if (unchanged.length) {
  console.log('\nStill not matched:')
  for (const name of unchanged) console.log(`- ${name}`)
}
