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

const ALIASES = {
  'NEW ENGLAND CABLE NEWS': ['NECN', 'NECNHD'],
  'NBC SPORTS BOSTON': ['NBCBOSHD', 'NBCBOS'],
  'NESN PLUS': ['NESNPLUSHD', 'NESNPLUS', 'NESN+'],
  'ESPN2': ['ESPN2', 'ESPN2HD'],
  'ESPN NEWS': ['ESPNNEWHD', 'ESPNEWS', 'ESPN NEWS'],
  'CBS SPORTS NETWORK': ['CBSSPTHD', 'CBS SPORTS', 'CBS SPORTS NETWORK'],
  'FOX SPORTS 1': ['FS1HD', 'FS1'],
  'FOX SPORTS 2': ['FS2HD', 'FS2'],
  'NFL NETWORK': ['NFLHD', 'NFLNET'],
  'NHL NETWORK': ['NHLTVHD', 'NHL NETWORK'],
  'MLB NETWORK': ['MLBHD', 'MLB NETWORK'],
  'NBA TV': ['NBAHD', 'NBA TV'],
  'TRUTV': ['TRUTVHD', 'TRUTV', 'TRU TV'],
  'FX MOVIE CHANNEL': ['FXMHD', 'FXM', 'FX MOVIE'],
  'COMEDY CENTRAL': ['COMEDYHD', 'COMEDY'],
  'BBC AMERICA': ['BBCAMHD', 'BBC AMERICA'],
  'FOOD NETWORK': ['FOODHD', 'FOOD'],
  'COOKING CHANNEL': ['COOKINGHD', 'COOKING'],
  'DISCOVERY CHANNEL': ['TDC-HD', 'DSC', 'DISCOVERY'],
  'DISCOVERY LIFE': ['DLIF', 'DISCOVERY LIFE'],
  'DISCOVERY FAMILY': ['DFCHHD', 'DFAM'],
  'DISCOVERY SCIENCE': ['SCIENCEHD', 'SCIENCE'],
  'INVESTIGATION DISCOVERY': ['INVSTDSCHD', 'ID'],
  'ANIMAL PLANET': ['ANIMALHD', 'ANIMAL'],
  'NAT GEO WILD': ['NGEOWILDHD', 'NGEOWILD'],
  'NATIONAL GEOGRAPHIC': ['NGCHD', 'NGC-E'],
  'SMITHSONIAN CHANNEL': ['SMITHSONHD', 'SMITHSONIAN'],
  'MAGNOLIA NETWORK': ['MAGNHD', 'MAGN'],
  'DESTINATION AMERICA': ['DESTAMERHD', 'DESTAMER'],
  'AMERICAN HEROES CHANNEL': ['AHCHD', 'AHC'],
  'FOX NEWS CHANNEL': ['FNCHD', 'FOXNEW', 'FOX NEWS'],
  'MS NOW': ['MSNBCHD', 'MSNBC', 'MSNOW'],
  'THE WEATHER CHANNEL': ['WEATHHD', 'WEATHER'],
  'DISNEY CHANNEL': ['DISNEYHD', 'DISNEY'],
  'CARTOON NETWORK': ['TOONHD', 'TOON'],
  'NICKELODEON': ['NICKHD', 'NICK', 'NIC-E'],
  'ADULT SWIM': ['ADULT SWIM', 'TOONHD', 'TOON'],
  'WE TV': ['WE-HD', 'WE'],
  'OXYGEN': ['OXYGENHD', 'OXGN-E'],
  'E!': ['ETV-HD', 'E!'],
  'MTV2': ['MTV2HD', 'MTV2'],
  'HALLMARK CHANNEL': ['HALLMARKHD', 'HALMRK'],
  'HALLMARK MYSTERY': ['HMMHD', 'HALLMYS'],
  'HALLMARK DRAMA': ['HALLDRMHD'],
  'GREAT AMERICAN FAMILY': ['GACFAM'],
  'UPTV': ['UPTVHD', 'UP TV'],
  'GAME SHOW NETWORK': ['GSNHD', 'GSN'],
  'AXS TV': ['AXSTV'],
  'CRIME AND INVESTIGATION': ['CRIMEINVHD', 'CRIMEINV'],
  'HBO': ['HBOHD', 'HBO'],
  'HBO HITS': ['HBO2HD', 'HBO HITS'],
  'HBO DRAMA': ['HBOSIGHD', 'HBO DRAMA'],
  'HBO COMEDY': ['HBOCOMHD', 'HBO COMEDY'],
  'CINEMAX': ['MAXHD', 'MAX'],
  'CINEMAX HITS': ['MOREMAXHD', 'MOREMAX', 'CINEMAX HITS'],
  'CINEMAX ACTION': ['ACTMAXHD', 'ACTMAX', 'CINEMAX ACTION'],
  'CINEMAX CLASSICS': ['5STARMAXHD', '5STARMAX', 'CINEMAX CLASSICS'],
  'PARAMOUNT+ WITH SHOWTIME': ['SHOHD', 'SHO'],
  'SHOXBET': ['SHOXBET', 'SHOBET', 'SHOWTIME BET'],
  'SHOWTIME 2': ['SHO2XEHD', 'SHO2', 'SHOWTIME 2'],
  'SHOWTIME EXTREME': ['SHOWEXHD', 'SHOX', 'SHOWTIME EXTREME'],
  'SHOWTIME FAMILY ZONE': ['SHOWFAM', 'SHOWTIME FAMILY'],
  'SHOWTIME NEXT': ['SHOWNEXT'],
  'SHOWTIME WOMEN': ['SHOWWOM'],
  'SHOWTIME SHOWCASE': ['SHWCASEHD', 'SHOWCASE'],
  'THE MOVIE CHANNEL': ['TMCHD', 'TMC'],
  'TMC XTRA': ['TMCXTRAHD', 'TMCXTRA'],
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
  'MGM+': ['MGM+'],
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
  const xmltvId = attr(attrs, 'xmltv_id')
  const names = [body.replace(/<[^>]+>/g, '').trim(), xmltvId.replace(/\.us$/i, '')].filter(Boolean)
  return { siteId, xmltvId, display: names[0], haystack: names.join(' ') }
})

console.log(`Loaded ${rawChannels.length} raw channels from ${inputFile}`)

const used = new Set()
const output = []
const missing = []

for (const target of MASTER) {
  const hit = findBest(target, rawChannels, used)
  if (!hit) {
    console.log(`[MISS] ${target}`)
    missing.push(target)
    continue
  }

  used.add(hit.siteId)
  const xmltv = `${safeXmltv(target)}.us`
  output.push(`  <channel site="tvguide.com" lang="en" xmltv_id="${escapeXml(xmltv)}" site_id="${escapeXml(hit.siteId)}">${escapeXml(target)}</channel>`)
  console.log(`[ADD] ${target} | ${hit.siteId} | raw=${hit.xmltvId} | display=${hit.display}`)
}

const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<channels>\n${output.join('\n')}\n</channels>\n`
fs.writeFileSync(outputFile, xml)

console.log(`\nWrote ${output.length} channels to ${outputFile}`)
console.log(`Missing ${missing.length} channel(s).`)
if (missing.length) {
  console.log('Missing list:')
  for (const m of missing) console.log(`- ${m}`)
}

function findBest(target, channels, used) {
  const aliases = [target, ...(ALIASES[target] || [])]
  const normalizedAliases = aliases.map(norm)

  const candidates = channels
    .filter(ch => ch.siteId && !used.has(ch.siteId))
    .map(ch => {
      const hay = norm(ch.haystack)
      let score = 0

      for (const a of normalizedAliases) {
        if (!a) continue
        if (hay === a) score = Math.max(score, 100)
        if (hay.includes(a)) score = Math.max(score, 85)
        if (a.includes(hay) && hay.length >= 3) score = Math.max(score, 70)
      }

      // Prefer HD-style matches when duplicates exist.
      if (/HD/i.test(ch.xmltvId) || /HD/i.test(ch.display)) score += 8

      // Avoid obvious west/feed duplicates unless target asks for them.
      if (/\bW\b|WEST/i.test(ch.xmltvId) && !/WEST/i.test(target)) score -= 20

      return { ch, score }
    })
    .filter(x => x.score > 0)
    .sort((a, b) => b.score - a.score)

  return candidates[0]?.ch || null
}

function norm(s) {
  return String(s || '')
    .toUpperCase()
    .replace(/&AMP;/g, '&')
    .replace(/\bAND\b/g, '&')
    .replace(/\+/g, 'PLUS')
    .replace(/[^A-Z0-9]+/g, '')
    .replace(/HIGHDEFINITION|HD$/g, 'HD')
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
  return m ? decodeXml(m[1]) : ''
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
