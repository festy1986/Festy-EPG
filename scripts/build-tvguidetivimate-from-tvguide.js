const fs = require('fs')
const path = require('path')

const INPUT = 'guides/tvguide.xml'
const OUTPUT = 'guides/tvguidetivimate.xml'

const MASTER = [
  ['NEW ENGLAND CABLE NEWS', ['NECN', 'NEW ENGLAND CABLE NEWS']],
  ['NESN', ['NESN', 'NEW ENGLAND SPORTS NETWORK']],
  ['NESN PLUS', ['NESNPLUSHD', 'NESN PLUS', 'NESN+', 'NEW ENGLAND SPORTS NETWORK PLUS']],
  ['NBC SPORTS BOSTON', ['NBC SPORTS BOSTON', 'NBCBOSHD']],

  ['ESPN', ['ESPN']],
  ['ESPN 2', ['ESPN2', 'ESPN 2']],
  ['ESPN NEWS', ['ESPNNEWHD', 'ESPNEWS', 'ESPN NEWS']],
  ['FOX SPORTS 1', ['FS1HD', 'FS1', 'FOX SPORTS 1']],
  ['FOX SPORTS 2', ['FS2', 'FOX SPORTS 2']],
  ['NFL NETWORK', ['NFLHD', 'NFLNET', 'NFL NETWORK']],
  ['NHL NETWORK', ['NHLTVHD', 'NHL NETWORK']],
  ['MLB NETWORK', ['MLBHD', 'MLB NETWORK']],
  ['NBA TV', ['NBAHD', 'NBA TV']],
  ['CBS SPORTS NETWORK', ['CBS SPORTS NETWORK', 'CBSSN']],

  ['USA NETWORK', ['USA', 'USA NETWORK']],
  ['TNT', ['TNT']],
  ['TBS', ['TBS']],
  ['TRU TV', ['TRUTV', 'TRU TV']],

  ['A&E', ['A&E']],
  ['AMC', ['AMC']],
  ['FX', ['FX']],
  ['FXX', ['FXX']],
  ['FXM', ['FXM', 'FX MOVIE CHANNEL']],
  ['SYFY', ['SYFY']],
  ['FREEFORM', ['FREEFRMHD', 'FREEFRM', 'FREEFORM']],
  ['PARAMOUNT NETWORK', ['PARMT', 'PARAMOUNT NETWORK']],
  ['COMEDY CENTRAL', ['COMEDYHD', 'COMEDY', 'COMEDY CENTRAL']],
  ['TV LAND', ['TVLAND', 'TV LAND']],
  ['BBC AMERICA', ['BBC AMERICA', 'BBC']],
  ['IFC', ['IFCHD', 'IFC']],

  ['HGTV', ['HGTV']],
  ['FOOD NETWORK', ['FOOD', 'FOOD NETWORK']],
  ['TRAVEL CHANNEL', ['TRAVEL CHANNEL', 'TRVL']],
  ['TLC', ['TLC']],
  ['DISCOVERY CHANNEL', ['DSC', 'DISCOVERY CHANNEL']],
  ['DISCOVERY FAMILY', ['DFCHHD', 'DFAM', 'DISCOVERY FAMILY']],
  ['DISCOVERY SCIENCE', ['SCIENCEHD', 'SCIENCE', 'DISCOVERY SCIENCE']],
  ['DISCOVERY LIFE', ['DLIF', 'DISCOVERY LIFE']],
  ['INVESTIGATION DISCOVERY', ['ID', 'INVESTIGATION DISCOVERY']],
  ['DESTINATION AMERICA', ['DESTAMERHD', 'DESTAMER', 'DESTINATION AMERICA']],
  ['MAGNOLIA', ['MAGNHD', 'MAGN', 'MAGNOLIA']],

  ['ANIMAL PLANET', ['ANIMALHD', 'ANIMAL', 'ANIMAL PLANET']],
  ['NATIONAL GEOGRAPHIC', ['NGCHD', 'NGC-E', 'NATIONAL GEOGRAPHIC']],
  ['NAT GEO WILD', ['NGEOWILDHD', 'NGEOWILD', 'NAT GEO WILD']],
  ['SMITHSONIAN CHANNEL', ['SMITHSONHD', 'SMITHSONIAN']],

  ['THE WEATHER CHANNEL', ['WEATHER CHANNEL', 'THE WEATHER CHANNEL']],

  ['BRAVO', ['BRAVO']],
  ['E! ENTERTAINMENT', ['E!', 'E ENTERTAINMENT']],
  ['MTV', ['MTV']],
  ['MTV 2', ['MTV2', 'MTV 2']],
  ['VH1', ['VH1']],
  ['CMT', ['CMTHD', 'CMT']],
  ['BET', ['BET']],
  ['OWN', ['OWN']],
  ['WE', ['WE', 'WE TV']],
  ['OXYGEN', ['OXYGENHD', 'OXYGEN']],
  ['LIFETIME', ['LIFE', 'LIFETIME']],
  ['LMN', ['LMN', 'LIFETIME MOVIE NETWORK']],
  ['POP', ['POPHD', 'POP']],
  ['VICE', ['VICEHD', 'VICE']],
  ['REELZ', ['REELZHD', 'REELZ']],
  ['FYI', ['FYIHD', 'FYI']],
  ['LOGO', ['LOGO']],
  ['FUSE', ['FUSEHD', 'FUSE']],
  ['OVATION', ['OVATHD', 'OVATION']],
  ['ASPIRE', ['ASPIRE']],
  ['UP TV', ['UPTVHD', 'UP TV', 'UPTV']],
  ['GREAT AMERICAN FAMILY', ['GACFAM', 'GREAT AMERICAN FAMILY']],

  ['DISNEY CHANNEL', ['DISNEYHD', 'DISNEY CHANNEL']],
  ['CARTOON NETWORK', ['CARTOON NETWORK', 'TOON']],
  ['NICKELODEON', ['NICKHD', 'NICK', 'NICKELODEON']],

  ['HALLMARK CHANNEL', ['HALLMARKHD', 'HALMRK', 'HALLMARK CHANNEL']],
  ['HALLMARK MYSTERY', ['HMMHD', 'HALLMYS', 'HALLMARK MYSTERY']],
  ['HALLMARK DRAMA', ['HALLDRMHD', 'HALLMARK DRAMA']],

  ['GAME SHOW NETWORK', ['GSNHD', 'GAME SHOW NETWORK']],
  ['INSP', ['INSPHD', 'INSP']],
  ['FETV', ['FETV']],
  ['TCM', ['TCMHD', 'TCM']],
  ['COOKING CHANNEL', ['COOKINGHD', 'COOKING CHANNEL']],
  ['AMERICAN HEROES CHANNEL', ['AHCHD', 'AHC', 'AMERICAN HEROES CHANNEL']],
  ['CRIME AND INVESTIGATION', ['CRIMEINVHD', 'CRIME AND INVESTIGATION']],

  ['ION PLUS', ['ION PLUS', 'ION+']],
  ['OUTDOOR CHANNEL', ['OUTHDE', 'OUTDOOR CHANNEL']],
  ['AWE', ['AWE', 'A WEALTH OF ENTERTAINMENT']],

  ['HBO', ['HBO']],
  ['HBO HITS', ['HBO HITS']],
  ['HBO DRAMA', ['HBO DRAMA']],
  ['HBO COMEDY', ['HBO COMEDY']],

  ['CINEMAX', ['CINEMAX']],
  ['CINEMAX HITS', ['CINEMAX HITS']],
  ['CINEMAX ACTION', ['CINEMAX ACTION']],
  ['CINEMAX CLASSICS', ['CINEMAX CLASSICS']],

  ['PARAMOUNT+ WITH SHOWTIME', ['PARAMOUNT+ WITH SHOWTIME']],
  ['SHOWTIME 2', ['SHOWTIME 2']],
  ['SHOWTIME EXTREME', ['SHOWTIME EXTREME']],
  ['SHOWTIME FAMILY ZONE', ['SHOWTIME FAMILY ZONE']],
  ['SHOWTIME NEXT', ['SHOWTIME NEXT']],
  ['SHOWTIME WOMEN', ['SHOWTIME WOMEN']],
  ['SHOWTIME SHOWCASE', ['SHOWTIME SHOWCASE', 'SHOWCASE']],

  ['THE MOVIE CHANNEL', ['THE MOVIE CHANNEL']],
  ['TMC XTRA', ['TMC XTRA', 'THE MOVIE CHANNEL XTRA']],
  ['FLIX', ['FLIX-E', 'FLIX']],

  ['STARZ', ['STARZ', 'STARZHD']],
  ['STARZ EDGE', ['STARZ EDGE']],
  ['STARZ CINEMA', ['STARZ CINEMA']],
  ['STARZ COMEDY', ['STARZ COMEDY']],
  ['STARZ ENCORE', ['STARZ ENCORE', 'ENCOREHD']],
  ['STARZ ENCORE ACTION', ['STARZ ENCORE ACTION', 'ENCRACTHD']],
  ['STARZ ENCORE BLACK', ['STARZ ENCORE BLACK', 'ENCRBLHD']],
  ['STARZ ENCORE CLASSIC', ['STARZ ENCORE CLASSIC', 'ENCRCLHD']],
  ['STARZ ENCORE SUSPENSE', ['STARZ ENCORE SUSPENSE', 'ENCORSHD']],
  ['STARZ ENCORE WESTERNS', ['STARZ ENCORE WESTERNS', 'ENCRWST']],
  ['STARZ ENCORE FAMILY', ['STARZ ENCORE FAMILY', 'ENCORFM']],
  ['STARZ KIDS & FAMILY', ['STARZ KIDS & FAMILY', 'STARZ KIDS AND FAMILY']],
  ['STARZ INBLACK', ['STARZ INBLACK', 'STARZ IN BLACK', 'STARZBLKHD']],

  ['MGM+', ['MGM+']],
  ['MGM+ HITS', ['MGM+ HITS']],
  ['MGM+ MARQUEE', ['MGM+ MARQUEE']],
  ['MGM+ DRIVE-IN', ['MGM+ DRIVE-IN']],

  ['MOVIEPLEX', ['MOVIEPLEX', 'PLEXHD']],
  ['INDIEPLEX', ['INDIEPLEX', 'INDIPX']]
]

function decodeXml(s) {
  return String(s || '')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
}

function escapeXml(s) {
  return String(s || '')
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function norm(s) {
  return decodeXml(s)
    .toUpperCase()
    .replace(/\+/g, ' PLUS ')
    .replace(/&/g, ' AND ')
    .replace(/[^A-Z0-9]+/g, ' ')
    .replace(/\bHD\b/g, '')
    .replace(/\bSD\b/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function getAttr(attrs, name) {
  const m = attrs.match(new RegExp(`\\b${name}="([^"]+)"`))
  return m ? m[1] : ''
}

function parseChannels(xml) {
  const channels = []
  const re = /<channel\b([^>]*)>([\s\S]*?)<\/channel>/g
  let m

  while ((m = re.exec(xml))) {
    const attrs = m[1]
    const body = m[2]

    let id = getAttr(attrs, 'id')
    const siteId = getAttr(attrs, 'site_id')

    if (!id && siteId) {
      id = siteId.includes('#') ? siteId.split('#').pop() : siteId
    }

    let name = ''

    const displayMatch = body.match(/<display-name[^>]*>([\s\S]*?)<\/display-name>/)
    if (displayMatch) {
      name = decodeXml(displayMatch[1]).trim()
    } else {
      name = decodeXml(body.replace(/<[^>]+>/g, '').trim())
    }

    if (!id || !name) continue

    channels.push({
      id,
      name,
      normName: norm(name)
    })
  }

  return channels
}

function findChannel(channels, aliases, usedIds) {
  const normalizedAliases = aliases.map(norm)

  for (const alias of normalizedAliases) {
    const exact = channels.find(ch => !usedIds.has(ch.id) && ch.normName === alias)
    if (exact) return exact
  }

  for (const alias of normalizedAliases) {
    const contains = channels.find(ch => !usedIds.has(ch.id) && ch.normName.includes(alias))
    if (contains) return contains
  }

  return null
}

if (!fs.existsSync(INPUT)) {
  console.error(`Missing input: ${INPUT}`)
  process.exit(1)
}

const xml = fs.readFileSync(INPUT, 'utf8')
const channels = parseChannels(xml)

console.log(`Found ${channels.length} raw channels in ${INPUT}`)

const usedIds = new Set()
const selected = []

for (const [wantedName, aliases] of MASTER) {
  const found = findChannel(channels, aliases, usedIds)

  if (!found) {
    console.log(`[missing] ${wantedName}`)
    continue
  }

  usedIds.add(found.id)
  selected.push({
    id: found.id,
    displayName: wantedName,
    sourceName: found.name
  })

  console.log(`[match] ${wantedName} <= ${found.name} (${found.id})`)
}

const selectedIds = new Set(selected.map(x => x.id))

const keptProgrammes = []
const programmeRe = /<programme\b([^>]*)>[\s\S]*?<\/programme>/g
let pm

while ((pm = programmeRe.exec(xml))) {
  const channelId = (pm[1].match(/\bchannel="([^"]+)"/) || [])[1]
  if (channelId && selectedIds.has(channelId)) {
    keptProgrammes.push(pm[0])
  }
}

const output = [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<tv>',
  ...selected.map(ch =>
    `  <channel id="${escapeXml(ch.id)}">\n    <display-name>${escapeXml(ch.displayName)}</display-name>\n  </channel>`
  ),
  ...keptProgrammes.map(p => p.replace(/^/gm, '  ')),
  '</tv>',
  ''
].join('\n')

fs.mkdirSync(path.dirname(OUTPUT), { recursive: true })
fs.writeFileSync(OUTPUT, output)

console.log(`Matched ${selected.length}/${MASTER.length} channels.`)
console.log(`Copied ${keptProgrammes.length} programme entries.`)
console.log(`Wrote ${OUTPUT}`)
