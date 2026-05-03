const fs = require('fs')

const inputFile = 'guides/tvguide.xml'
const outputFile = 'guides/tvguidetivimate.xml'

const MASTER = [
  'NEW ENGLAND CABLE NEWS',
  'NESN',
  'NESN PLUS',
  'NBC SPORTS BOSTON',
  'ESPN',
  'ESPN2',
  'ESPN NEWS',
  'CBS SPORTS NETWORK',
  'CBS SPORTS HQ',
  'FOX SPORTS 1',
  'FOX SPORTS 2',
  'NFL NETWORK',
  'NHL NETWORK',
  'MLB NETWORK',
  'NBA TV',
  'USA NETWORK',
  'TNT',
  'TBS',
  'TRUTV',
  'A&E',
  'AMC',
  'FX',
  'FXX',
  'FX MOVIE CHANNEL',
  'SYFY',
  'PARAMOUNT NETWORK',
  'COMEDY CENTRAL',
  'TV LAND',
  'IFC',
  'BBC AMERICA',
  'POP',
  'VICE',
  'REELZ',
  'FUSE',
  'LOGO',
  'HGTV',
  'FOOD NETWORK',
  'TRAVEL CHANNEL',
  'COOKING CHANNEL',
  'TLC',
  'DISCOVERY CHANNEL',
  'DISCOVERY LIFE',
  'DISCOVERY FAMILY',
  'DISCOVERY SCIENCE',
  'INVESTIGATION DISCOVERY',
  'ANIMAL PLANET',
  'NAT GEO WILD',
  'NATIONAL GEOGRAPHIC',
  'SMITHSONIAN CHANNEL',
  'MAGNOLIA NETWORK',
  'DESTINATION AMERICA',
  'AMERICAN HEROES CHANNEL',
  'CNN',
  'HLN',
  'CNBC',
  'FOX NEWS CHANNEL',
  'MS NOW',
  'THE WEATHER CHANNEL',
  'DISNEY CHANNEL',
  'CARTOON NETWORK',
  'NICKELODEON',
  'ADULT SWIM',
  'LIFETIME',
  'LMN',
  'WE TV',
  'OXYGEN',
  'BRAVO',
  'E!',
  'VH1',
  'MTV',
  'MTV2',
  'CMT',
  'BET',
  'OWN',
  'HALLMARK CHANNEL',
  'HALLMARK MYSTERY',
  'HALLMARK DRAMA',
  'GREAT AMERICAN FAMILY',
  'UPTV',
  'ASPIRE',
  'AWE',
  'OVATION',
  'TCM',
  'ION PLUS',
  'ION MYSTERY',
  'COURT TV',
  'ANTENNA TV',
  'COZI TV',
  'OUTDOOR CHANNEL',
  'GAME SHOW NETWORK',
  'INSP',
  'FETV',
  'AXS TV',
  'CRIME AND INVESTIGATION',
  'HBO',
  'HBO HITS',
  'HBO DRAMA',
  'HBO COMEDY',
  'CINEMAX',
  'CINEMAX HITS',
  'CINEMAX ACTION',
  'CINEMAX CLASSICS',
  'PARAMOUNT+ WITH SHOWTIME',
  'SHOXBET',
  'SHOWTIME 2',
  'SHOWTIME EXTREME',
  'SHOWTIME FAMILY ZONE',
  'SHOWTIME NEXT',
  'SHOWTIME WOMEN',
  'SHOWTIME SHOWCASE',
  'THE MOVIE CHANNEL',
  'TMC XTRA',
  'FLIX',
  'STARZ',
  'STARZ EDGE',
  'STARZ CINEMA',
  'STARZ COMEDY',
  'STARZ ENCORE',
  'STARZ ENCORE ACTION',
  'STARZ ENCORE BLACK',
  'STARZ ENCORE CLASSIC',
  'STARZ ENCORE SUSPENSE',
  'STARZ ENCORE FAMILY',
  'STARZ KIDS & FAMILY',
  'STARZ INBLACK',
  'MGM+',
  'MGM+ HITS',
  'MGM+ MARQUEE',
  'MGM+ DRIVE-IN',
  'MOVIEPLEX',
  'INDIEPLEX'
]

const DIRECT_ALIASES = {
  'NEW ENGLAND CABLE NEWS': ['NECN', 'NECNHD'],
  'NESN PLUS': ['NESNPLUSHD', 'NESNPLUS'],
  'NBC SPORTS BOSTON': ['NBCBOSHD', 'NBCBOS'],
  'ESPN2': ['ESPN2', 'ESPN2HD'],
  'ESPN NEWS': ['ESPNNEWHD', 'ESPNEWS'],
  'CBS SPORTS NETWORK': ['CBSSPTHD'],
  'FOX SPORTS 1': ['FS1HD', 'FS1'],
  'FOX SPORTS 2': ['FS2HD', 'FS2'],
  'NFL NETWORK': ['NFLHD', 'NFLNET'],
  'NHL NETWORK': ['NHLTVHD'],
  'MLB NETWORK': ['MLBHD'],
  'NBA TV': ['NBAHD'],
  'TRUTV': ['TRUTVHD', 'TRUTV'],
  'FX MOVIE CHANNEL': ['FXMHD', 'FXM'],
  'COMEDY CENTRAL': ['COMEDYHD', 'COMEDY'],
  'BBC AMERICA': ['BBCAMHD'],
  'FOOD NETWORK': ['FOODHD', 'FOOD'],
  'COOKING CHANNEL': ['COOKINGHD'],
  'DISCOVERY CHANNEL': ['TDC-HD', 'DSC'],
  'DISCOVERY LIFE': ['DLIF'],
  'DISCOVERY FAMILY': ['DFCHHD', 'DFAM'],
  'DISCOVERY SCIENCE': ['SCIENCEHD', 'SCIENCE'],
  'INVESTIGATION DISCOVERY': ['INVSTDSCHD', 'ID'],
  'ANIMAL PLANET': ['ANIMALHD', 'ANIMAL'],
  'NAT GEO WILD': ['NGEOWILDHD', 'NGEOWILD'],
  'NATIONAL GEOGRAPHIC': ['NGCHD', 'NGC-E'],
  'SMITHSONIAN CHANNEL': ['SMITHSONHD'],
  'MAGNOLIA NETWORK': ['MAGNHD', 'MAGN'],
  'DESTINATION AMERICA': ['DESTAMERHD', 'DESTAMER'],
  'AMERICAN HEROES CHANNEL': ['AHCHD', 'AHC'],
  'FOX NEWS CHANNEL': ['FNCHD', 'FOXNEW'],
  'MS NOW': ['MSNBC', 'MSNBCHD', 'MSNOW'],
  'THE WEATHER CHANNEL': ['WEATHHD'],
  'DISNEY CHANNEL': ['DISNEYHD', 'DISNEY'],
  'CARTOON NETWORK': ['TOONHD', 'TOON'],
  'NICKELODEON': ['NICKHD', 'NICK', 'NIC-E'],
  'WE TV': ['WE-HD', 'WE'],
  'OXYGEN': ['OXYGENHD', 'OXGN-E'],
  'MTV2': ['MTV2HD', 'MTV2'],
  'HALLMARK CHANNEL': ['HALLMARKHD', 'HALMRK'],
  'HALLMARK MYSTERY': ['HMMHD', 'HALLMYS'],
  'HALLMARK DRAMA': ['HALLDRMHD'],
  'GREAT AMERICAN FAMILY': ['GACFAM'],
  'UPTV': ['UPTVHD'],
  'GAME SHOW NETWORK': ['GSNHD', 'GSN'],
  'AXS TV': ['AXSTV'],
  'CRIME AND INVESTIGATION': ['CRIMEINVHD'],
  'HBO': ['HBOHD', 'HBO'],
  'HBO HITS': ['HBO2HD'],
  'HBO DRAMA': ['HBOSIGHD'],
  'HBO COMEDY': ['HBOCOMHD'],
  'CINEMAX': ['MAXHD', 'MAX'],
  'CINEMAX HITS': ['MOREMAXHD'],
  'CINEMAX ACTION': ['ACTMAXHD'],
  'CINEMAX CLASSICS': ['5STARMAXHD'],
  'PARAMOUNT+ WITH SHOWTIME': ['SHOHD'],
  'SHOXBET': ['SHOXBET'],
  'SHOWTIME 2': ['SHO2XEHD'],
  'SHOWTIME EXTREME': ['SHOWEXHD'],
  'SHOWTIME FAMILY ZONE': ['SHOWFAM'],
  'SHOWTIME NEXT': ['SHOWNEXT'],
  'SHOWTIME WOMEN': ['SHOWWOM'],
  'SHOWTIME SHOWCASE': ['SHWCASEHD'],
  'THE MOVIE CHANNEL': ['TMCHD', 'TMC'],
  'TMC XTRA': ['TMCXTRAHD'],
  'FLIX': ['FLIX-E'],
  'STARZ': ['STARZHD', 'STARZ'],
  'STARZ EDGE': ['STARZEDHD'],
  'STARZ CINEMA': ['STARZCINHD'],
  'STARZ COMEDY': ['STARZCOMHD'],
  'STARZ ENCORE': ['ENCOREHD'],
  'STARZ ENCORE ACTION': ['ENCRACTHD'],
  'STARZ ENCORE BLACK': ['ENCRBLHD'],
  'STARZ ENCORE CLASSIC': ['ENCRCLHD'],
  'STARZ ENCORE SUSPENSE': ['ENCORSHD'],
  'STARZ ENCORE FAMILY': ['ENCORFM'],
  'STARZ KIDS & FAMILY': ['STARZFAMHD'],
  'STARZ INBLACK': ['STARZBLKHD'],
  'MGM+ HITS': ['MGM+HIT'],
  'MGM+ MARQUEE': ['MGM+MAR'],
  'MGM+ DRIVE-IN': ['MGM+DRV'],
  'MOVIEPLEX': ['PLEXHD'],
  'INDIEPLEX': ['INDIPX']
}

if (!fs.existsSync(inputFile)) {
  console.error(`Missing ${inputFile}`)
  process.exit(1)
}

const raw = fs.readFileSync(inputFile, 'utf8')

const rawChannels = [...raw.matchAll(/<channel\s+([^>]+)>([\s\S]*?)<\/channel>/g)].map(m => {
  const attrs = m[1]
  const body = m[2]
  const siteId = attr(attrs, 'site_id')
  const xmltvId = decodeXml(attr(attrs, 'xmltv_id')).replace(/\.us$/i, '')
  const display = decodeXml(body.replace(/<[^>]+>/g, '').trim())
  return { siteId, xmltvId, display }
})

const byExact = new Map()
for (const ch of rawChannels) {
  for (const key of [ch.display, ch.xmltvId]) {
    const n = norm(key)
    if (!byExact.has(n)) byExact.set(n, [])
    byExact.get(n).push(ch)
  }
}

const used = new Set()
const out = []
const miss = []

for (const target of MASTER) {
  const names = [target, ...(DIRECT_ALIASES[target] || [])]
  let hit = null

  for (const name of names) {
    const list = byExact.get(norm(name)) || []
    hit = pickBest(list.filter(ch => !used.has(ch.siteId)))
    if (hit) break
  }

  if (!hit) {
    console.log(`[MISS] ${target}`)
    miss.push(target)
    continue
  }

  used.add(hit.siteId)

  out.push(
    `  <channel site="tvguide.com" lang="en" xmltv_id="${escapeXml(safeXmltv(target) + '.us')}" site_id="${escapeXml(hit.siteId)}">${escapeXml(target)}</channel>`
  )

  console.log(`[ADD] ${target} | ${hit.siteId} | raw=${hit.xmltvId} | display=${hit.display}`)
}

fs.writeFileSync(
  outputFile,
  `<?xml version="1.0" encoding="UTF-8"?>\n<channels>\n${out.join('\n')}\n</channels>\n`
)

console.log(`\nWrote ${out.length} channel(s) to ${outputFile}`)
console.log(`Missing ${miss.length} channel(s).`)
if (miss.length) {
  console.log('Missing:')
  for (const m of miss) console.log(`- ${m}`)
}

function pickBest(list) {
  if (!list.length) return null
  return [...list].sort((a, b) => score(b) - score(a))[0]
}

function score(ch) {
  let s = 0
  if (/HD$/i.test(ch.xmltvId) || /HD$/i.test(ch.display)) s += 10
  if (/-W$/i.test(ch.xmltvId) || /WEST/i.test(ch.display)) s -= 20
  return s
}

function norm(s) {
  return String(s || '')
    .toUpperCase()
    .replace(/&AMP;/g, '&')
    .replace(/\+/g, 'PLUS')
    .replace(/[^A-Z0-9]/g, '')
}

function safeXmltv(s) {
  return String(s)
    .replace(/&/g, 'And')
    .replace(/\+/g, 'PLUS')
    .replace(/!/g, '')
    .replace(/[^A-Za-z0-9]+/g, '.')
    .replace(/\.+/g, '.')
    .replace(/^\.|\.$/g, '')
}

function attr(attrs, name) {
  const m = attrs.match(new RegExp(`${name}="([^"]*)"`, 'i'))
  return m ? m[1] : ''
}

function decodeXml(s) {
  return String(s)
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
}

function escapeXml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}
