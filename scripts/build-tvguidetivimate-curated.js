const fs = require('fs')

const RAW_FILE = 'guides/tvguide.xml'
const OUTPUT_FILE = 'guides/tvguidetivimate.xml'

const MASTER = [
  'COMET',
  'LAFF',
  'FOX PORTLAND',
  'NBC PORTLAND',
  'ABC PORTLAND',
  'CBS PORTLAND',
  'CW PORTLAND',
  'PBS',
  'METV',
  'ION MYSTERY',
  'COZI TV',
  'COURT TV',
  'GRIT',
  'ANTENNA TV',
  'HEROES & ICONS',

  'NEW ENGLAND CABLE NEWS',
  'NESN',
  'NESN PLUS',
  'NBC SPORTS BOSTON',

  'ESPN',
  'ESPN 2 HD',
  'ESPN NEWS',
  'FOX SPORTS 1',
  'FOX SPORTS 2',
  'NFL NETWORK',
  'NBA TV',
  'MLB NETWORK',
  'NHL NETWORK',
  'CBS SPORTS NETWORK',

  'CNN',
  'HLN',
  'CNBC',
  'FOX NEWS',
  'MS NOW',

  'USA NETWORK',
  'TNT',
  'TBS',
  'TRU TV',
  'A&E',
  'AMC',
  'FX',
  'FXX',
  'FXM',
  'SYFY',

  'HGTV',
  'FOOD NETWORK',
  'TRAVEL CHANNEL',
  'TLC',
  'DISCOVERY CHANNEL',
  'DISCOVERY LIFE',
  'DISCOVERY FAMILY',
  'DISCOVERY SCIENCE',
  'INVESTIGATION DISCOVERY',
  'ANIMAL PLANET',
  'HISTORY CHANNEL',
  'NATIONAL GEOGRAPHIC',
  'NAT GEO WILD',
  'SMITHSONIAN CHANNEL',

  'BRAVO',
  'E! ENTERTAINMENT',
  'MTV',
  'MTV 2',
  'VH1',
  'CMT',
  'BET',
  'OWN',
  'WE',
  'OXYGEN',
  'LIFETIME',
  'LMN',
  'POP',
  'VICE',
  'REELZ',
  'FYI',
  'LOGO',
  'FUSE',
  'OVATION',
  'ASPIRE',
  'UP TV',
  'GREAT AMERICAN FAMILY',

  'DISNEY CHANNEL',
  'CARTOON NETWORK',
  'NICKELODEON',

  'HALLMARK CHANNEL',
  'HALLMARK MYSTERY',
  'HALLMARK DRAMA',

  'GAME SHOW NETWORK',
  'INSP',
  'FETV',
  'TCM',
  'COOKING CHANNEL',
  'OUTDOOR CHANNEL',
  'AMERICAN HEROES CHANNEL',
  'CRIME AND INVESTIGATION',
  'MAGNOLIA',
  'THE WEATHER CHANNEL',
  'PARAMOUNT NETWORK',
  'COMEDY CENTRAL',
  'TV LAND',
  'BBC AMERICA',
  'FREEFORM',

  // Current HBO / Max linear names
  'HBO',
  'HBO 2',
  'HBO Signature',
  'HBO Comedy',
  'HBO Family',
  'HBO Latino',

  // Current Cinemax family
  'Cinemax',
  'MoreMax',
  'ActionMax',
  'ThrillerMax',
  'MovieMax',
  '5StarMax',
  'OuterMax',

  // Paramount+ / Showtime family
  'Paramount+ with SHOWTIME',
  'SHOWTIME 2',
  'SHOWTIME EXTREME',
  'SHOWTIME FAMILY ZONE',
  'SHOWTIME NEXT',
  'SHOWTIME WOMEN',
  'SHOWTIME SHOWCASE',

  // STARZ / ENCORE
  'STARZ',
  'STARZ Edge',
  'STARZ Cinema',
  'STARZ Comedy',
  'STARZ ENCORE',
  'STARZ ENCORE ACTION',
  'STARZ ENCORE BLACK',
  'STARZ ENCORE CLASSIC',
  'STARZ ENCORE SUSPENSE',
  'STARZ ENCORE WESTERNS',
  'STARZ ENCORE FAMILY',
  'STARZ Kids & Family',
  'STARZ InBlack',

  // MGM+
  'MGM+',
  'MGM+ Hits',
  'MGM+ Marquee',
  'MGM+ Drive-In',

  // Other premium/movie channels
  'MoviePlex',
  'RetroPlex',
  'IndiePlex',
  'Flix',
  'The Movie Channel',
  'TMC Xtra'
]

const OTA = [
  { name: 'COMET', tests: [/WPFO.*DT3/i, /COMET/i] },
  { name: 'LAFF', tests: [/WMTW.*DT3/i, /LAFF/i] },
  { name: 'METV', tests: [/WMTW.*DT2/i] },
  { name: 'NBC PORTLAND', tests: [/WCSH/i] },
  { name: 'ABC PORTLAND', tests: [/WMTW(?!.*DT2)(?!.*DT3)/i] },
  { name: 'CBS PORTLAND', tests: [/WGME(?!.*DT2)(?!.*DT3)/i] },
  { name: 'FOX PORTLAND', tests: [/WGME.*DT2/i] },
  { name: 'CW PORTLAND', tests: [/WPXT(?!.*DT2)(?!.*DT3)/i] },
  { name: 'ION MYSTERY', tests: [/WPXT.*DT3/i] },
  { name: 'PBS', tests: [/WCBB/i] },
  { name: 'HEROES & ICONS', tests: [/H(&amp;|&)I/i, /HEROES/i] },
  { name: 'COZI TV', tests: [/COZI/i] },
  { name: 'COURT TV', tests: [/COURT/i] },
  { name: 'GRIT', tests: [/GRIT/i] },
  { name: 'ANTENNA TV', tests: [/ANTENNA/i] }
]

const ALIASES = {
  'NEW ENGLAND CABLE NEWS': [/^NECN$/i, /NECN/i],
  'GAME SHOW NETWORK': [/^GSN/i, /GAME SHOW/i],
  'DISCOVERY CHANNEL': [/^TDC/i, /DISCOVERY/i],
  'USA NETWORK': [/^USA/i],
  NESN: [/^NESNHD$/i, /^NESN$/i],
  'NESN PLUS': [/NESNPLUS/i],
  'NBC SPORTS BOSTON': [/NBCBOS/i],
  'ESPN 2 HD': [/ESPN2/i],
  'MS NOW': [/MSNOW/i, /MSNBC/i],
  'FOX NEWS': [/FOXNEW/i, /FNCHD/i],
  'THE WEATHER CHANNEL': [/WEATH/i],
  'TRU TV': [/TRUTV/i],
  'NATIONAL GEOGRAPHIC': [/^NGC/i, /NGCHD/i],
  'NAT GEO WILD': [/NGEOWILD/i],
  'HALLMARK CHANNEL': [/HALMRK/i, /HALLMARKHD/i],
  'HALLMARK MYSTERY': [/HALLMYS/i, /HMMHD/i],
  'HALLMARK DRAMA': [/HALLDRM/i],
  'DISCOVERY SCIENCE': [/SCIENCE/i],
  'DISCOVERY FAMILY': [/DFCH/i, /DISCOVERY FAMILY/i],
  'AMERICAN HEROES CHANNEL': [/AHC/i],
  'CRIME AND INVESTIGATION': [/CRIMEINV/i],
  'INVESTIGATION DISCOVERY': [/INVSTD/i, /^ID$/i],
  'COOKING CHANNEL': [/COOKING/i],
  'FOX SPORTS 1': [/FS1/i],
  'FOX SPORTS 2': [/FS2/i],
  'CBS SPORTS NETWORK': [/CBSSPT/i],
  'ESPN NEWS': [/ESPNNEW/i],
  'UP TV': [/UPTV/i],
  'GREAT AMERICAN FAMILY': [/GACFAM/i],
  'E! ENTERTAINMENT': [/ETV/i],
  FXM: [/FXM/i],
  'MTV 2': [/MTV2/i],
  FREEFORM: [/FREEFRM/i],
  'PARAMOUNT NETWORK': [/PARMT/i],
  'COMEDY CENTRAL': [/CMDY/i, /COMEDY/i],
  'TV LAND': [/TVLAND/i],
  'BBC AMERICA': [/BBCAM/i],
  MAGNOLIA: [/MAGN/i],
  OVATION: [/OVAT/i],
  ASPIRE: [/ASPIRE/i],

  HBO: [/^HBOHD$/i, /^HBO$/i],
  'HBO 2': [/HBO2HD/i, /HBO2/i],
  'HBO Signature': [/HBOSIG/i, /HBOS/i],
  'HBO Comedy': [/HBOCOM/i, /HBOC/i],
  'HBO Family': [/HBOFAM/i, /HBO FAMILY/i],
  'HBO Latino': [/HBOLAT/i, /HBOL/i],

  Cinemax: [/^MAXHD$/i, /^CINEMAX$/i],
  MoreMax: [/MOREMAX/i],
  ActionMax: [/ACTMAX/i, /ACTIONMAX/i],
  ThrillerMax: [/THRILLERMAX/i],
  MovieMax: [/MOVIEMAX/i],
  '5StarMax': [/5STARMAX/i],
  OuterMax: [/OUTERMAX/i],

  'Paramount+ with SHOWTIME': [/^SHOHD$/i, /PARAMOUNT.*SHOWTIME/i],
  'SHOWTIME 2': [/SHO2/i],
  'SHOWTIME EXTREME': [/SHOWEX/i, /SHOX/i],
  'SHOWTIME FAMILY ZONE': [/SHOWFAM/i, /SHOFAM/i],
  'SHOWTIME NEXT': [/SHOWNEXT/i, /SHNXT/i],
  'SHOWTIME WOMEN': [/SHOWWOM/i],
  'SHOWTIME SHOWCASE': [/SHWCASE/i, /SHOCSE/i],

  STARZ: [/^STARZHD$/i, /^STARZ$/i],
  'STARZ Edge': [/STARZED/i, /STARZ EDGE/i],
  'STARZ Cinema': [/STARZCIN/i],
  'STARZ Comedy': [/STARZCOM/i],
  'STARZ ENCORE': [/^ENCOREHD/i, /STARZ ENCORE$/i],
  'STARZ ENCORE ACTION': [/ENCRACT/i, /ENCORE.*ACTION/i],
  'STARZ ENCORE BLACK': [/ENCRBL/i, /ENCORE.*BLACK/i],
  'STARZ ENCORE CLASSIC': [/ENCRCL/i, /ENCORE.*CLASSIC/i],
  'STARZ ENCORE SUSPENSE': [/ENCORS/i, /ENCORE.*SUSPENSE/i],
  'STARZ ENCORE WESTERNS': [/ENCRWST/i, /ENCORE.*WEST/i],
  'STARZ ENCORE FAMILY': [/ENCORFM/i, /ENCORE.*FAMILY/i],
  'STARZ Kids & Family': [/STARZFAM/i, /KIDS.*FAMILY/i],
  'STARZ InBlack': [/STARZBLK/i, /INBLACK/i],

  'MGM+': [/^MGM\+$/i, /^MGM\+HD/i],
  'MGM+ Hits': [/MGM.*HIT/i],
  'MGM+ Marquee': [/MGM.*MAR/i],
  'MGM+ Drive-In': [/MGM.*DRV/i, /DRIVE/i],

  MoviePlex: [/PLEXHD/i, /MOVIEPLEX/i],
  RetroPlex: [/RETRO/i],
  IndiePlex: [/INDIPX/i, /INDIE/i],
  Flix: [/FLIX-E/i, /^FLIX$/i],
  'The Movie Channel': [/^TMCHD/i, /MOVIE CHANNEL/i],
  'TMC Xtra': [/TMCXTRA/i]
}

function main() {
  if (!fs.existsSync(RAW_FILE)) {
    console.error(`Missing raw input file: ${RAW_FILE}`)
    process.exit(1)
  }

  const xml = fs.readFileSync(RAW_FILE, 'utf8')
  const raw = parseChannels(xml)

  if (!raw.length) {
    console.error(`No channels found in ${RAW_FILE}`)
    process.exit(1)
  }

  console.log(`Loaded ${raw.length} raw channels from ${RAW_FILE}`)

  const selected = []
  const usedIds = new Set()
  const usedNames = new Set()

  for (const ota of OTA) {
    const match = raw.find(ch => {
      const hay = `${ch.text} ${ch.xmltv_id} ${ch.site_id}`
      return ota.tests.every(rx => rx.test(hay))
    })

    add(selected, usedIds, usedNames, match, ota.name, 'OTA')
  }

  for (const name of MASTER) {
    if (usedNames.has(name)) continue

    const match = findBest(raw, name)
    add(selected, usedIds, usedNames, match, name, 'MASTER')
  }

  selected.sort((a, b) => MASTER.indexOf(a.name) - MASTER.indexOf(b.name))

  const output = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<channels>',
    ...selected.map(ch => {
      return `  <channel site="tvguide.com" lang="en" xmltv_id="${escapeXml(makeXmltvId(ch.name))}" site_id="${escapeXml(ch.site_id)}">${escapeXml(ch.name)}</channel>`
    }),
    '</channels>',
    ''
  ].join('\n')

  fs.writeFileSync(OUTPUT_FILE, output)

  console.log(`Wrote ${selected.length} curated channels to ${OUTPUT_FILE}`)
}

function parseChannels(xml) {
  return [...xml.matchAll(/<channel\b([^>]*)>([\s\S]*?)<\/channel>/g)]
    .map(m => {
      const attrs = parseAttrs(m[1])
      return {
        xmltv_id: decodeXml(attrs.xmltv_id || ''),
        site_id: decodeXml(attrs.site_id || ''),
        text: decodeXml(m[2].trim())
      }
    })
    .filter(ch => ch.site_id)
}

function parseAttrs(str) {
  const attrs = {}
  const re = /([a-zA-Z0-9_:-]+)="([^"]*)"/g
  let m

  while ((m = re.exec(str))) {
    attrs[m[1]] = m[2]
  }

  return attrs
}

function findBest(raw, wanted) {
  const aliases = ALIASES[wanted] || [
    new RegExp(`^${escapeRegex(shortCode(wanted))}$`, 'i'),
    new RegExp(escapeRegex(wanted.replace(/\s+/g, '.*')), 'i')
  ]

  const matches = raw
    .map(ch => {
      const hay = `${ch.text} ${ch.xmltv_id}`
      let score = 0

      for (const rx of aliases) {
        if (rx.test(hay)) score += 100
      }

      if (/HD/i.test(ch.text) || /HD/i.test(ch.xmltv_id)) score += 10
      if (/\bSD\b/i.test(ch.text) || /\bSD\b/i.test(ch.xmltv_id)) score -= 5

      // Avoid west feeds unless the wanted name explicitly asks for west.
      if (/\bWEST\b|\b-W\b|WAL\b/i.test(hay) && !/WEST/i.test(wanted)) score -= 30

      // Avoid generic LOCAL unless specifically OTA/local.
      if (/LOCAL/i.test(hay) && !/PORTLAND|PBS/i.test(wanted)) score -= 50

      return { ch, score }
    })
    .filter(x => x.score > 0)
    .sort((a, b) => b.score - a.score)

  return matches[0]?.ch || null
}

function add(selected, usedIds, usedNames, raw, name, reason) {
  if (!raw) {
    console.log(`[MISS ${reason}] ${name}`)
    return
  }

  if (!raw.site_id) {
    console.log(`[MISS ID] ${name}`)
    return
  }

  if (usedNames.has(name)) {
    console.log(`[SKIP DUP NAME] ${name}`)
    return
  }

  if (usedIds.has(raw.site_id)) {
    console.log(`[SKIP DUP SITE_ID] ${name} | ${raw.site_id} | raw=${raw.xmltv_id || raw.text}`)
    return
  }

  usedNames.add(name)
  usedIds.add(raw.site_id)

  selected.push({
    name,
    site_id: raw.site_id
  })

  console.log(`[ADD ${reason}] ${name} | ${raw.site_id} | raw=${raw.xmltv_id || raw.text}`)
}

function shortCode(name) {
  return name
    .replace(/CHANNEL|NETWORK|ENTERTAINMENT|PLUS/g, '')
    .replace(/&/g, '')
    .replace(/\+/g, '')
    .replace(/\s+/g, '')
    .toUpperCase()
}

function makeXmltvId(name) {
  return name
    .replace(/&/g, 'And')
    .replace(/\+/g, 'Plus')
    .replace(/[^A-Za-z0-9]+/g, '.')
    .replace(/^\.+|\.+$/g, '')
    .concat('.us')
}

function escapeXml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function decodeXml(value) {
  return String(value || '')
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
}

function escapeRegex(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

main()
