const fs = require('fs')
const path = require('path')

const RAW_FILE = 'guides/tvguide.xml'
const OUT_FILE = 'guides/tvguidetivimate.xml'

function escapeXml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function decodeXml(value) {
  return String(value)
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
}

function norm(value) {
  return String(value || '')
    .toUpperCase()
    .replace(/&AMP;/g, '&')
    .replace(/[^A-Z0-9]+/g, '')
}

function xmltvId(name) {
  return `${String(name)
    .replace(/&/g, 'And')
    .replace(/\+/g, 'Plus')
    .replace(/[^A-Za-z0-9]+/g, '.')
    .replace(/^\.+|\.+$/g, '')}.us`
}

function readRawChannels(file) {
  if (!fs.existsSync(file)) {
    throw new Error(`Missing raw file: ${file}`)
  }

  const xml = fs.readFileSync(file, 'utf8')
  const channels = []

  const re = /<channel\b([^>]*)>([\s\S]*?)<\/channel>/g
  let match

  while ((match = re.exec(xml))) {
    const attrs = match[1]
    const text = decodeXml(match[2].trim())

    const siteId = (attrs.match(/\bsite_id="([^"]+)"/) || [])[1]
    const rawXmltv = decodeXml((attrs.match(/\bxmltv_id="([^"]+)"/) || [])[1] || '')

    if (!siteId) continue

    channels.push({
      site_id: siteId,
      xmltv_id: rawXmltv,
      name: text,
      nXmltv: norm(rawXmltv),
      nName: norm(text),
      haystack: norm(`${rawXmltv} ${text}`)
    })
  }

  return channels
}

const curated = [
  // Portland OTA / local
  {
    name: 'NBC PORTLAND',
    prefer: ['WCSHHD', 'WCSH']
  },
  {
    name: 'ABC PORTLAND',
    prefer: ['WMTWHD', 'WMTW']
  },
  {
    name: 'CBS PORTLAND',
    prefer: ['WGMEHD', 'WGME']
  },
  {
    name: 'FOX PORTLAND',
    prefer: ['WGFODT2', 'WGMEDT2', 'WPFOHD', 'WPFO']
  },
  {
    name: 'CW PORTLAND',
    prefer: ['WPXTHD', 'WPXT']
  },
  {
    name: 'PBS',
    prefer: ['WCBBHD', 'WCBB', 'WENHHD', 'WENH']
  },
  {
    name: 'METV',
    prefer: ['WMTWDT2', 'METV']
  },
  {
    name: 'HEROES & ICONS',
    prefer: ['WPXTDT2', 'H&I', 'HEROESICONS', 'HANDI']
  },
  {
    name: 'ION MYSTERY',
    prefer: ['WPXTDT3', 'IONMYSTERY']
  },
  {
    name: 'COMET',
    prefer: ['COMET', 'COMETTV']
  },
  {
    name: 'LAFF',
    prefer: ['LAFF']
  },
  {
    name: 'GRIT',
    prefer: ['GRIT']
  },
  {
    name: 'COZI TV',
    prefer: ['COZI', 'COZITV']
  },
  {
    name: 'COURT TV',
    prefer: ['COURTTV']
  },
  {
    name: 'ANTENNA TV',
    prefer: ['ANTENNATV']
  },

  // News / locals
  { name: 'NEW ENGLAND CABLE NEWS', prefer: ['NECNHD', 'NECN'] },
  { name: 'MS NOW', prefer: ['MSNBCHD', 'MSNBC'] },
  { name: 'CNN', prefer: ['CNNHD', 'CNN'] },
  { name: 'HLN', prefer: ['HLNHD', 'HLN'] },
  { name: 'CNBC', prefer: ['CNBCHD', 'CNBC'] },
  { name: 'FOX NEWS', prefer: ['FNCHD', 'FOXNEWSHD', 'FNC'] },

  // Sports
  { name: 'NESN', prefer: ['NESNHD', 'NESN'] },
  { name: 'NESN PLUS', prefer: ['NESNPLUSHD', 'NESNPLUS'] },
  { name: 'NBC SPORTS BOSTON', prefer: ['NBCBOSHD', 'NBCSPORTSBOSTON', 'NBCSBOSTON'] },
  { name: 'ESPN', prefer: ['ESPNHD', 'ESPN'] },
  { name: 'ESPN 2 HD', prefer: ['ESPN2HD', 'ESPN2'] },
  { name: 'ESPN NEWS', prefer: ['ESPNNEWHD', 'ESPNEWSHD', 'ESPNEWS'] },
  { name: 'FOX SPORTS 1', prefer: ['FS1HD', 'FS1'] },
  { name: 'FOX SPORTS 2', prefer: ['FS2HD', 'FS2'] },
  { name: 'NFL NETWORK', prefer: ['NFLHD', 'NFLNETHD', 'NFLNET', 'NFLNETWORK'] },
  { name: 'NBA TV', prefer: ['NBATVHD', 'NBAHD', 'NBATV'] },
  { name: 'MLB NETWORK', prefer: ['MLBHD', 'MLBNHD', 'MLBNET', 'MLBNETWORK'] },
  { name: 'NHL NETWORK', prefer: ['NHLHD', 'NHLNETHD', 'NHLNET', 'NHLNETWORK'] },
  { name: 'CBS SPORTS NETWORK', prefer: ['CBSSPTHD', 'CBSSPORTSHD', 'CBSSPORTS'] },

  // Entertainment / cable
  { name: 'USA NETWORK', prefer: ['USAHD', 'USA'] },
  { name: 'TNT', prefer: ['TNTHD', 'TNT'] },
  { name: 'TBS', prefer: ['TBSHD', 'TBS'] },
  { name: 'TRU TV', prefer: ['TRUTVHD', 'TRUTV'] },
  { name: 'A&E', prefer: ['A&EHD', 'AEHD', 'AETVHD'] },
  { name: 'AMC', prefer: ['AMCHD', 'AMC'] },
  { name: 'FX', prefer: ['FXHD', 'FX'] },
  { name: 'FXX', prefer: ['FXXHD', 'FXX'] },
  { name: 'FXM', prefer: ['FXMHD', 'FXM'] },
  { name: 'SYFY', prefer: ['SYFYHD', 'SYFY'] },
  { name: 'FREEFORM', prefer: ['FREEFRMHD', 'FREEFORMHD', 'FREEFORM'] },
  { name: 'PARAMOUNT NETWORK', prefer: ['PARMTHD', 'PARMT', 'PARAMOUNTNETWORK'] },
  { name: 'COMEDY CENTRAL', prefer: ['COMEDYHD', 'COMEDYCENTRAL'] },
  { name: 'TV LAND', prefer: ['TVLANDHD', 'TVLAND'] },
  { name: 'BBC AMERICA', prefer: ['BBCAMHD', 'BBCAMERICA'] },
  { name: 'IFC', prefer: ['IFCHD', 'IFC'] },

  // Lifestyle / factual
  { name: 'HGTV', prefer: ['HGTVHD', 'HGTV'] },
  { name: 'FOOD NETWORK', prefer: ['FOODHD', 'FOODNETWORKHD', 'FOODNETWORK'] },
  { name: 'TRAVEL CHANNEL', prefer: ['TRVLHD', 'TRAVELHD', 'TRAVELCHANNEL'] },
  { name: 'TLC', prefer: ['TLCHD', 'TLC'] },
  { name: 'DISCOVERY CHANNEL', prefer: ['TDCHD', 'DISCOVERYHD', 'DISCOVERYCHANNEL'] },
  { name: 'DISCOVERY LIFE', prefer: ['DLIFEHD', 'DISCOVERYLIFE'] },
  { name: 'DISCOVERY FAMILY', prefer: ['DFCHHD', 'DISCOVERYFAMILY'] },
  { name: 'DISCOVERY SCIENCE', prefer: ['SCIENCEHD', 'SCIENCE', 'DISCOVERYSCIENCE'] },
  { name: 'INVESTIGATION DISCOVERY', prefer: ['INVSTDSCHD', 'IDHD', 'INVESTIGATIONDISCOVERY'] },
  { name: 'ANIMAL PLANET', prefer: ['APLHD', 'ANIMALPLANETHD', 'ANIMALPLANET'] },
  { name: 'HISTORY CHANNEL', prefer: ['HISTORYHD', 'HISTHD', 'HISTORY'] },
  { name: 'NATIONAL GEOGRAPHIC', prefer: ['NGCHD', 'NATGEOHD', 'NATIONALGEOGRAPHIC'] },
  { name: 'NAT GEO WILD', prefer: ['NGEOWILDHD', 'NATGEOWILD'] },
  { name: 'SMITHSONIAN CHANNEL', prefer: ['SMITHHD', 'SMITHSONIANHD', 'SMITHSONIAN'] },
  { name: 'MAGNOLIA', prefer: ['MAGNHD', 'MAGNOLIA'] },
  { name: 'THE WEATHER CHANNEL', prefer: ['WEATHHD', 'WEATHERCHANNEL'] },

  // General entertainment
  { name: 'BRAVO', prefer: ['BRAVOHD', 'BRAVO'] },
  { name: 'E! ENTERTAINMENT', prefer: ['ETVHD', 'EHD', 'EENTERTAINMENT'] },
  { name: 'MTV', prefer: ['MTVHD', 'MTV'] },
  { name: 'MTV 2', prefer: ['MTV2HD', 'MTV2'] },
  { name: 'VH1', prefer: ['VH1HD', 'VH1'] },
  { name: 'CMT', prefer: ['CMTHD', 'CMT'] },
  { name: 'BET', prefer: ['BETHD', 'BET'] },
  { name: 'OWN', prefer: ['OWNHD', 'OWN'] },
  { name: 'WE', prefer: ['WEHD', 'WETVHD'] },
  { name: 'OXYGEN', prefer: ['OXYGENHD', 'OXYGEN'] },
  { name: 'LIFETIME', prefer: ['LIFEHD', 'LIFETIMEHD', 'LIFETIME'] },
  { name: 'LMN', prefer: ['LMNHD', 'LMN'] },
  { name: 'POP', prefer: ['POPHD', 'POP'] },
  { name: 'VICE', prefer: ['VICEHD', 'VICE'] },
  { name: 'REELZ', prefer: ['REELZHD', 'REELZ'] },
  { name: 'FYI', prefer: ['FYIHD', 'FYI'] },
  { name: 'LOGO', prefer: ['LOGOHD', 'LOGO'] },
  { name: 'FUSE', prefer: ['FUSEHD', 'FUSE'] },
  { name: 'OVATION', prefer: ['OVATHD', 'OVATION'] },
  { name: 'ASPIRE', prefer: ['ASPIREHD', 'ASPIRE'] },
  { name: 'UP TV', prefer: ['UPTVHD', 'UPTV'] },
  { name: 'GREAT AMERICAN FAMILY', prefer: ['GACFAMHD', 'GACFAM', 'GREATAMERICANFAMILY'] },

  // Kids
  { name: 'DISNEY CHANNEL', prefer: ['DISNHD', 'DISNEYHD', 'DISNEYCHANNEL'] },
  { name: 'CARTOON NETWORK', prefer: ['TOONHD', 'CARTOONHD', 'CARTOONNETWORK'] },
  { name: 'NICKELODEON', prefer: ['NICKHD', 'NICKELODEONHD', 'NICKELODEON'] },

  // Hallmark / classics
  { name: 'HALLMARK CHANNEL', prefer: ['HALLMARKHD', 'HALLMARK'] },
  { name: 'HALLMARK MYSTERY', prefer: ['HMMHD', 'HALLMARKMYSTERY'] },
  { name: 'HALLMARK DRAMA', prefer: ['HALLDRMHD', 'HALLMARKDRAMA'] },
  { name: 'GAME SHOW NETWORK', prefer: ['GSNHD', 'GAMESHOWNETWORK'] },
  { name: 'INSP', prefer: ['INSPHD', 'INSP'] },
  { name: 'FETV', prefer: ['FETVHD', 'FETV'] },
  { name: 'TCM', prefer: ['TCMHD', 'TCM'] },
  { name: 'COOKING CHANNEL', prefer: ['COOKINGHD', 'COOKINGCHANNEL'] },
  { name: 'OUTDOOR CHANNEL', prefer: ['OUTDHD', 'OUTDOORHD', 'OUTDOORCHANNEL'] },
  { name: 'AMERICAN HEROES CHANNEL', prefer: ['AHCHD', 'AMERICANHEROES'] },
  { name: 'CRIME AND INVESTIGATION', prefer: ['CRIMEINVHD', 'CRIMEINVESTIGATION'] },

  // Premiums
  { name: 'HBO', prefer: ['HBOHD', 'HBO'] },
  { name: 'HBO 2', prefer: ['HBO2HD', 'HBO2'] },
  { name: 'HBO SIGNATURE', prefer: ['HBOSIGHD', 'HBOSIGNATURE'] },
  { name: 'HBO COMEDY', prefer: ['HBOCOMHD', 'HBOCOMEDY'] },
  { name: 'HBO FAMILY', prefer: ['HBOFAMHD', 'HBOFAMILY'] },
  { name: 'HBO ZONE', prefer: ['HBOZONEHD', 'HBOZONE'] },
  { name: 'HBO LATINO', prefer: ['HBOLATHD', 'HBOLATINO'] },

  { name: 'CINEMAX', prefer: ['MAXHD', 'CINEMAXHD', 'CINEMAX'] },
  { name: 'MOREMAX', prefer: ['MOREMAXHD', 'MOREMAX'] },
  { name: 'ACTIONMAX', prefer: ['ACTMAXHD', 'ACTIONMAX'] },
  { name: 'THRILLERMAX', prefer: ['THRMAXHD', 'THRILLERMAX'] },
  { name: 'MOVIEMAX', prefer: ['MOVIEMAXHD', 'MOVIEMAX'] },
  { name: '5STARMAX', prefer: ['5STARMAXHD', '5STARMAX'] },
  { name: 'OUTERMAX', prefer: ['OUTERMAXHD', 'OUTERMAX'] },

  { name: 'PARAMOUNT+ WITH SHOWTIME', prefer: ['SHOWTIMEHD', 'SHOHD', 'PARAMOUNTSHOWTIME'] },
  { name: 'SHOWTIME 2', prefer: ['SHO2XEHD', 'SHOWTIME2HD', 'SHOWTIME2'] },
  { name: 'SHOWTIME EXTREME', prefer: ['SHOWEXHD', 'SHOWTIMEEXTREME'] },
  { name: 'SHOWTIME FAMILY ZONE', prefer: ['SHOWFAMHD', 'SHOWFAM', 'SHOWTIMEFAMILY'] },
  { name: 'SHOWTIME NEXT', prefer: ['SHOWNEXTHD', 'SHOWNEXT'] },
  { name: 'SHOWTIME WOMEN', prefer: ['SHOWWOMHD', 'SHOWWOM'] },
  { name: 'SHOWTIME SHOWCASE', prefer: ['SHWCASEHD', 'SHOWCASEHD'] },
  { name: 'THE MOVIE CHANNEL', prefer: ['TMCHD', 'THEMOVIECHANNEL'] },
  { name: 'TMC XTRA', prefer: ['TMCXTRAHD', 'TMCXTRA'] },
  { name: 'FLIX', prefer: ['FLIXHD', 'FLIX'] },

  { name: 'STARZ', prefer: ['STARZHD', 'STARZ'] },
  { name: 'STARZ EDGE', prefer: ['STARZEDHD', 'STARZEDGE'] },
  { name: 'STARZ CINEMA', prefer: ['STARZCINHD', 'STARZCINEMA'] },
  { name: 'STARZ COMEDY', prefer: ['STARZCOMHD', 'STARZCOMEDY'] },
  { name: 'STARZ ENCORE', prefer: ['ENCOREHD', 'STARZENCORE'] },
  { name: 'STARZ ENCORE ACTION', prefer: ['ENCRACTHD', 'ENCOREACTION'] },
  { name: 'STARZ ENCORE BLACK', prefer: ['ENCRBLHD', 'ENCOREBLACK'] },
  { name: 'STARZ ENCORE CLASSIC', prefer: ['ENCRCLHD', 'ENCORECLASSIC'] },
  { name: 'STARZ ENCORE SUSPENSE', prefer: ['ENCORSHD', 'ENCORESUSPENSE'] },
  { name: 'STARZ ENCORE WESTERNS', prefer: ['ENCRWSTHD', 'ENCRWST', 'ENCOREWESTERNS'] },
  { name: 'STARZ ENCORE FAMILY', prefer: ['ENCORFMHD', 'ENCORFM', 'ENCOREFAMILY'] },
  { name: 'STARZ KIDS & FAMILY', prefer: ['STARZFAMHD', 'STARZKIDSFAMILY'] },
  { name: 'STARZ INBLACK', prefer: ['STARZBLKHD', 'STARZINBLACK'] },

  { name: 'MGM+', prefer: ['MGMHD', 'MGMPLUSHD', 'MGMPLUS', 'MGM'] },
  { name: 'MGM+ HITS', prefer: ['MGMHITSHD', 'MGMHIT', 'MGMPLUS HITS'] },
  { name: 'MGM+ MARQUEE', prefer: ['MGMMARQUEEHD', 'MGMMAR', 'MGMPLUSMARQUEE'] },
  { name: 'MGM+ DRIVE-IN', prefer: ['MGMDRIVEINHD', 'MGMDRV', 'MGMPLUSDRIVEIN'] },
  { name: 'MOVIEPLEX', prefer: ['PLEXHD', 'MOVIEPLEX'] },
  { name: 'RETROPLEX', prefer: ['RETROPLEXHD', 'RETROPLEX'] },
  { name: 'INDIEPLEX', prefer: ['INDIPXHD', 'INDIPX', 'INDIEPLEX'] }
]

function scoreCandidate(channel, target) {
  const rawId = norm(channel.xmltv_id.replace(/\.US$/i, ''))
  const rawName = norm(channel.name)
  const hay = channel.haystack

  for (let i = 0; i < target.prefer.length; i++) {
    const p = norm(target.prefer[i])
    if (!p) continue

    if (rawId === p) return 10000 - i
    if (rawName === p) return 9500 - i
    if (hay === p) return 9000 - i
    if (rawId.includes(p)) return 8000 - i
    if (rawName.includes(p)) return 7500 - i
    if (hay.includes(p)) return 7000 - i
  }

  const targetNorm = norm(target.name)
  if (rawName === targetNorm) return 5000
  if (rawId === targetNorm) return 4800

  return 0
}

function findBest(rawChannels, target, usedSiteIds) {
  const blocked = new Set(['LOCAL'])

  let best = null

  for (const ch of rawChannels) {
    if (usedSiteIds.has(ch.site_id)) continue
    if (blocked.has(ch.nName) || blocked.has(ch.nXmltv)) continue

    const score = scoreCandidate(ch, target)
    if (!score) continue

    if (!best || score > best.score) {
      best = { channel: ch, score }
    }
  }

  return best ? best.channel : null
}

function main() {
  const rawChannels = readRawChannels(RAW_FILE)
  console.log(`Loaded ${rawChannels.length} raw channels from ${RAW_FILE}`)

  const usedSiteIds = new Set()
  const output = []

  for (const target of curated) {
    const found = findBest(rawChannels, target, usedSiteIds)

    if (!found) {
      console.log(`[MISS] ${target.name}`)
      continue
    }

    usedSiteIds.add(found.site_id)

    output.push({
      name: target.name,
      xmltv_id: xmltvId(target.name),
      site_id: found.site_id,
      raw: found.xmltv_id || found.name
    })

    console.log(`[ADD] ${target.name} | ${found.site_id} | raw=${found.xmltv_id || found.name}`)
  }

  const xml = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<channels>',
    ...output.map(ch =>
      `  <channel site="tvguide.com" lang="en" xmltv_id="${escapeXml(ch.xmltv_id)}" site_id="${escapeXml(ch.site_id)}">${escapeXml(ch.name)}</channel>`
    ),
    '</channels>',
    ''
  ].join('\n')

  fs.mkdirSync(path.dirname(OUT_FILE), { recursive: true })
  fs.writeFileSync(OUT_FILE, xml)

  console.log(`Wrote ${output.length} curated channels to ${OUT_FILE}`)

  const misses = curated.length - output.length
  if (misses > 0) {
    console.log(`Missing ${misses} channel(s). Check [MISS] lines above.`)
  }
}

main()
