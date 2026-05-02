const fs = require('fs')
const path = require('path')

const INPUT = 'guides/tvguide.xml'
const OUTPUT = 'guides/tvguidetivimate.xml'

const MASTER = [
  ['NEW ENGLAND CABLE NEWS', ['NECN', 'NEW ENGLAND CABLE NEWS']],
  ['NESN', ['NESN', 'NEW ENGLAND SPORTS NETWORK']],
  ['NESN PLUS', ['NESN PLUS', 'NESN+', 'NEW ENGLAND SPORTS NETWORK PLUS']],
  ['NBC SPORTS BOSTON', ['NBC SPORTS BOSTON', 'BOSTON SPORTS']],

  ['ESPN', ['ESPN']],
  ['ESPN 2', ['ESPN2', 'ESPN 2']],
  ['ESPN NEWS', ['ESPNEWS', 'ESPN NEWS']],
  ['FOX SPORTS 1', ['FOX SPORTS 1', 'FS1']],
  ['FOX SPORTS 2', ['FOX SPORTS 2', 'FS2']],
  ['NFL NETWORK', ['NFL NETWORK']],
  ['NHL NETWORK', ['NHL NETWORK']],
  ['MLB NETWORK', ['MLB NETWORK']],
  ['NBA TV', ['NBA TV', 'NBAHD']],
  ['CBS SPORTS NETWORK', ['CBS SPORTS NETWORK', 'CBSSN']],

  ['USA NETWORK', ['USA NETWORK', 'USA']],
  ['TNT', ['TNT']],
  ['TBS', ['TBS']],
  ['TRU TV', ['TRU TV', 'TRUTV']],

  ['A&E', ['A&E', 'A AND E']],
  ['AMC', ['AMC']],
  ['FX', ['FX']],
  ['FXX', ['FXX']],
  ['FXM', ['FXM', 'FX MOVIE CHANNEL']],
  ['SYFY', ['SYFY']],
  ['FREEFORM', ['FREEFORM']],
  ['PARAMOUNT NETWORK', ['PARAMOUNT NETWORK']],
  ['COMEDY CENTRAL', ['COMEDY CENTRAL']],
  ['TV LAND', ['TV LAND']],
  ['BBC AMERICA', ['BBC AMERICA']],
  ['IFC', ['IFC']],

  ['HGTV', ['HGTV']],
  ['FOOD NETWORK', ['FOOD NETWORK']],
  ['TRAVEL CHANNEL', ['TRAVEL CHANNEL']],
  ['TLC', ['TLC']],
  ['DISCOVERY CHANNEL', ['DISCOVERY CHANNEL', 'DISCOVERY']],
  ['DISCOVERY FAMILY', ['DISCOVERY FAMILY', 'DISCOVERY FAMILY CHANNEL']],
  ['DISCOVERY SCIENCE', ['DISCOVERY SCIENCE', 'SCIENCE CHANNEL', 'SCIENCE']],
  ['DISCOVERY LIFE', ['DISCOVERY LIFE', 'DISCOVERY LIFE CHANNEL']],
  ['INVESTIGATION DISCOVERY', ['INVESTIGATION DISCOVERY', 'ID']],
  ['DESTINATION AMERICA', ['DESTINATION AMERICA']],
  ['MAGNOLIA', ['MAGNOLIA', 'MAGNOLIA NETWORK']],

  ['ANIMAL PLANET', ['ANIMAL PLANET', 'ANIMAL']],
  ['NATIONAL GEOGRAPHIC', ['NATIONAL GEOGRAPHIC', 'NATIONAL GEOGRAPHIC CHANNEL', 'NGC']],
  ['NAT GEO WILD', ['NAT GEO WILD', 'NATIONAL GEOGRAPHIC WILD']],
  ['SMITHSONIAN CHANNEL', ['SMITHSONIAN CHANNEL', 'SMITHSONIAN']],

  ['THE WEATHER CHANNEL', ['THE WEATHER CHANNEL', 'WEATHER CHANNEL']],

  ['BRAVO', ['BRAVO']],
  ['E! ENTERTAINMENT', ['E!', 'E ENTERTAINMENT']],
  ['MTV', ['MTV']],
  ['MTV 2', ['MTV2', 'MTV 2']],
  ['VH1', ['VH1']],
  ['CMT', ['CMT']],
  ['BET', ['BET']],
  ['OWN', ['OWN']],
  ['WE', ['WE TV', 'WETV', 'WE']],
  ['OXYGEN', ['OXYGEN']],
  ['LIFETIME', ['LIFETIME']],
  ['LMN', ['LMN', 'LIFETIME MOVIE NETWORK']],
  ['POP', ['POP']],
  ['VICE', ['VICE']],
  ['REELZ', ['REELZ']],
  ['FYI', ['FYI']],
  ['LOGO', ['LOGO']],
  ['FUSE', ['FUSE']],
  ['OVATION', ['OVATION']],
  ['ASPIRE', ['ASPIRE']],
  ['UP TV', ['UP TV', 'UPTV']],
  ['GREAT AMERICAN FAMILY', ['GREAT AMERICAN FAMILY', 'GAC FAMILY']],

  ['DISNEY CHANNEL', ['DISNEY CHANNEL']],
  ['CARTOON NETWORK', ['CARTOON NETWORK']],
  ['NICKELODEON', ['NICKELODEON', 'NICK']],

  ['HALLMARK CHANNEL', ['HALLMARK CHANNEL']],
  ['HALLMARK MYSTERY', ['HALLMARK MYSTERY', 'HALLMARK MOVIES & MYSTERIES']],
  ['HALLMARK DRAMA', ['HALLMARK DRAMA']],

  ['GAME SHOW NETWORK', ['GAME SHOW NETWORK', 'GSN']],
  ['INSP', ['INSP']],
  ['FETV', ['FETV']],
  ['TCM', ['TCM', 'TURNER CLASSIC MOVIES']],
  ['COOKING CHANNEL', ['COOKING CHANNEL']],
  ['AMERICAN HEROES CHANNEL', ['AMERICAN HEROES CHANNEL', 'AHC']],
  ['CRIME AND INVESTIGATION', ['CRIME AND INVESTIGATION', 'CRIME & INVESTIGATION']],

  ['ION PLUS', ['ION PLUS', 'ION+']],
  ['OUTDOOR CHANNEL', ['OUTDOOR CHANNEL']],
  ['AWE', ['AWE', 'A WEALTH OF ENTERTAINMENT']],

  ['HBO', ['HBO']],
  ['HBO HITS', ['HBO HITS']],
  ['HBO DRAMA', ['HBO DRAMA']],
  ['HBO COMEDY', ['HBO COMEDY']],

  ['CINEMAX', ['CINEMAX']],
  ['CINEMAX HITS', ['CINEMAX HITS']],
  ['CINEMAX ACTION', ['CINEMAX ACTION']],
  ['CINEMAX CLASSICS', ['CINEMAX CLASSICS']],

  ['PARAMOUNT+ WITH SHOWTIME', ['PARAMOUNT+ WITH SHOWTIME', 'PARAMOUNT PLUS WITH SHOWTIME']],
  ['SHOWTIME 2', ['SHOWTIME 2']],
  ['SHOWTIME EXTREME', ['SHOWTIME EXTREME']],
  ['SHOWTIME FAMILY ZONE', ['SHOWTIME FAMILY ZONE']],
  ['SHOWTIME NEXT', ['SHOWTIME NEXT']],
  ['SHOWTIME WOMEN', ['SHOWTIME WOMEN']],
  ['SHOWTIME SHOWCASE', ['SHOWTIME SHOWCASE', 'SHOWCASE']],

  ['THE MOVIE CHANNEL', ['THE MOVIE CHANNEL']],
  ['TMC XTRA', ['TMC XTRA', 'THE MOVIE CHANNEL XTRA']],
  ['FLIX', ['FLIX']],

  ['STARZ', ['STARZ']],
  ['STARZ EDGE', ['STARZ EDGE']],
  ['STARZ CINEMA', ['STARZ CINEMA']],
  ['STARZ COMEDY', ['STARZ COMEDY']],
  ['STARZ ENCORE', ['STARZ ENCORE']],
  ['STARZ ENCORE ACTION', ['STARZ ENCORE ACTION']],
  ['STARZ ENCORE BLACK', ['STARZ ENCORE BLACK']],
  ['STARZ ENCORE CLASSIC', ['STARZ ENCORE CLASSIC']],
  ['STARZ ENCORE SUSPENSE', ['STARZ ENCORE SUSPENSE']],
  ['STARZ ENCORE WESTERNS', ['STARZ ENCORE WESTERNS']],
  ['STARZ ENCORE FAMILY', ['STARZ ENCORE FAMILY']],
  ['STARZ KIDS & FAMILY', ['STARZ KIDS & FAMILY', 'STARZ KIDS AND FAMILY']],
  ['STARZ INBLACK', ['STARZ INBLACK', 'STARZ IN BLACK']],

  ['MGM+', ['MGM+', 'MGM PLUS']],
  ['MGM+ HITS', ['MGM+ HITS', 'MGM PLUS HITS']],
  ['MGM+ MARQUEE', ['MGM+ MARQUEE', 'MGM PLUS MARQUEE']],
  ['MGM+ DRIVE-IN', ['MGM+ DRIVE-IN', 'MGM PLUS DRIVE-IN']],

  ['MOVIEPLEX', ['MOVIEPLEX']],
  ['INDIEPLEX', ['INDIEPLEX']]
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
    .replace(/\bEAST\b/g, '')
    .replace(/\bWEST\b/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function matchScore(rawName, aliases) {
  const n = norm(rawName)
  let best = 0

  for (const alias of aliases) {
    const a = norm(alias)

    if (n === a) best = Math.max(best, 100)
    else if (n.includes(a)) best = Math.max(best, 85)
    else if (a.includes(n)) best = Math.max(best, 70)
  }

  return best
}

function parseChannels(xml) {
  const channels = []

  const xmltvRe = /<channel\b([^>]*)>([\s\S]*?)<\/channel>/g
  let m

  while ((m = xmltvRe.exec(xml))) {
    const attrs = m[1]
    const body = m[2]

    const idMatch = attrs.match(/\bid="([^"]+)"/)
    const siteIdMatch = attrs.match(/\bsite_id="([^"]+)"/)
    const nameMatch = body.match(/<display-name[^>]*>([\s\S]*?)<\/display-name>/) || body.match(/<channel[^>]*>([\s\S]*?)<\/channel>/)

    let id = idMatch ? idMatch[1] : null
    const siteId = siteIdMatch ? siteIdMatch[1] : null

    if (!id && siteId) {
      id = siteId.includes('#') ? siteId.split('#').pop() : siteId
    }

    let name = ''
    const textOnly = body.replace(/<[^>]+>/g, '').trim()
    if (nameMatch) name = decodeXml(nameMatch[1]).trim()
    else if (textOnly) name = decodeXml(textOnly).trim()

    if (id && name) {
      channels.push({
        id,
        siteId,
        name,
        original: m[0]
      })
    }
  }

  return channels
}

function chooseBestChannels(channels) {
  const chosen = []
  const usedIds = new Set()

  for (const [wantedName, aliases] of MASTER) {
    const candidates = channels
      .map(ch => ({ ch, score: matchScore(ch.name, aliases) }))
      .filter(x => x.score >= 85)
      .sort((a, b) => b.score - a.score)

    const best = candidates.find(x => !usedIds.has(x.ch.id))

    if (best) {
      usedIds.add(best.ch.id)
      chosen.push({
        wantedName,
        id: best.ch.id,
        sourceName: best.ch.name,
        score: best.score
      })
    } else {
      console.log(`[missing] ${wantedName}`)
    }
  }

  return chosen
}

function buildOutputXml(inputXml, chosen) {
  const chosenIds = new Set(chosen.map(c => c.id))

  const programmes = []
  const progRe = /<programme\b([^>]*)>[\s\S]*?<\/programme>/g
  let m

  while ((m = progRe.exec(inputXml))) {
    const attrs = m[1]
    const channelMatch = attrs.match(/\bchannel="([^"]+)"/)
    if (channelMatch && chosenIds.has(channelMatch[1])) {
      programmes.push(m[0])
    }
  }

  const channelXml = chosen.map(c => {
    return `  <channel id="${escapeXml(c.id)}">\n    <display-name>${escapeXml(c.wantedName)}</display-name>\n  </channel>`
  })

  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<tv>',
    ...channelXml,
    ...programmes.map(p => p.replace(/^/gm, '  ')),
    '</tv>',
    ''
  ].join('\n')
}

if (!fs.existsSync(INPUT)) {
  console.error(`Missing input file: ${INPUT}`)
  process.exit(1)
}

const inputXml = fs.readFileSync(INPUT, 'utf8')
const channels = parseChannels(inputXml)

if (!channels.length) {
  console.error(`No channels found in ${INPUT}`)
  process.exit(1)
}

const chosen = chooseBestChannels(channels)

if (!chosen.length) {
  console.error('No master-list channels matched.')
  process.exit(1)
}

fs.mkdirSync(path.dirname(OUTPUT), { recursive: true })

const outputXml = buildOutputXml(inputXml, chosen)
fs.writeFileSync(OUTPUT, outputXml)

console.log(`Matched ${chosen.length}/${MASTER.length} channels.`)
console.log(`Wrote ${OUTPUT}`)
for (const c of chosen) {
  console.log(`[match] ${c.wantedName} <= ${c.sourceName} (${c.id})`)
}
