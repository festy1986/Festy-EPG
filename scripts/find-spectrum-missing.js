const fs = require('fs')

const PROVIDER_ID = process.env.TVGUIDE_PROVIDER_ID || '9100002976'
const OUTPUT = process.env.OUTPUT || 'channels/spectrum-missing-candidates.channels.xml'

const BASE = 'https://backend.tvguide.com/tvschedules/tvguide'

const WANTED = [
  { name: 'NHL NETWORK', terms: ['NHL NETWORK', 'NHL'] },
  { name: 'CBS SPORTS HQ', terms: ['CBS SPORTS HQ', 'CBS SPORTS H'] },

  { name: 'NATIONAL GEOGRAPHIC', terms: ['NATIONAL GEOGRAPHIC', 'NAT GEO'] },
  { name: 'ANIMAL PLANET', terms: ['ANIMAL PLANET', 'ANIMAL'] },
  { name: 'HISTORY CHANNEL', terms: ['HISTORY CHANNEL', 'HISTORY'] },
  { name: 'DESTINATION AMERICA', terms: ['DESTINATION AMERICA'] },
  { name: 'DISCOVERY LIFE', terms: ['DISCOVERY LIFE'] },
  { name: 'SMITHSONIAN CHANNEL', terms: ['SMITHSONIAN'] },
  { name: 'AMC PLUS', terms: ['AMC+', 'AMC PLUS'] },

  { name: 'OUTDOOR CHANNEL', terms: ['OUTDOOR CHANNEL', 'OUTDOOR'] },
  { name: 'AWE', terms: ['AWE', 'A WEALTH OF ENTERTAINMENT', 'WEALTH'] },
  { name: 'COZI TV', terms: ['COZI', 'COZI TV'] },

  // HBO / Cinemax current names
  { name: 'HBO', terms: ['HBO'] },
  { name: 'HBO HITS', terms: ['HBO HITS', 'HBO2', 'HBO 2'] },
  { name: 'HBO DRAMA', terms: ['HBO DRAMA', 'HBO SIGNATURE'] },
  { name: 'HBO COMEDY', terms: ['HBO COMEDY'] },
  { name: 'HBO MOVIES', terms: ['HBO MOVIES', 'HBO ZONE'] },
  { name: 'HBO LATINO', terms: ['HBO LATINO'] },

  { name: 'CINEMAX', terms: ['CINEMAX'] },
  { name: 'CINEMAX HITS', terms: ['CINEMAX HITS', 'MOREMAX'] },
  { name: 'CINEMAX ACTION', terms: ['CINEMAX ACTION', 'ACTIONMAX'] },
  { name: 'CINEMAX CLASSICS', terms: ['CINEMAX CLASSICS', '5STARMAX', '5 STAR MAX'] },

  // Showtime / Paramount
  { name: 'PARAMOUNT+ WITH SHOWTIME', terms: ['PARAMOUNT+ WITH SHOWTIME', 'PARAMOUNT PLUS WITH SHOWTIME', 'SHOWTIME HD', 'SHOWTIME'] },
  { name: 'SHOWTIME 2', terms: ['SHOWTIME 2', 'SHO2'] },
  { name: 'SHOWTIME EXTREME', terms: ['SHOWTIME EXTREME'] },
  { name: 'SHOWTIME FAMILY ZONE', terms: ['SHOWTIME FAMILY ZONE'] },
  { name: 'SHOWTIME NEXT', terms: ['SHOWTIME NEXT'] },
  { name: 'SHOWTIME WOMEN', terms: ['SHOWTIME WOMEN'] },
  { name: 'SHOWCASE', terms: ['SHOWCASE', 'SHOWTIME SHOWCASE'] },
  { name: 'SHOXBET', terms: ['SHOXBET', 'SHO X BET', 'SHO×BET', 'SHOWTIME BET'] },
  { name: 'THE MOVIE CHANNEL', terms: ['THE MOVIE CHANNEL'] },
  { name: 'TMC XTRA', terms: ['TMC XTRA', 'MOVIE CHANNEL XTRA'] },
  { name: 'FLIX', terms: ['FLIX'] },

  // Starz
  { name: 'STARZ', terms: ['STARZ'] },
  { name: 'STARZ EDGE', terms: ['STARZ EDGE'] },
  { name: 'STARZ CINEMA', terms: ['STARZ CINEMA'] },
  { name: 'STARZ COMEDY', terms: ['STARZ COMEDY'] },
  { name: 'STARZ ENCORE', terms: ['STARZ ENCORE'] },
  { name: 'STARZ ENCORE ACTION', terms: ['STARZ ENCORE ACTION'] },
  { name: 'STARZ ENCORE BLACK', terms: ['STARZ ENCORE BLACK'] },
  { name: 'STARZ ENCORE CLASSIC', terms: ['STARZ ENCORE CLASSIC'] },
  { name: 'STARZ ENCORE FAMILY', terms: ['STARZ ENCORE FAMILY'] },
  { name: 'STARZ ENCORE SUSPENSE', terms: ['STARZ ENCORE SUSPENSE'] },
  { name: 'STARZ KIDS & FAMILY', terms: ['STARZ KIDS', 'STARZ KIDS & FAMILY'] },
  { name: 'STARZ IN BLACK', terms: ['STARZ INBLACK', 'STARZ IN BLACK'] },

  // MGM / Plex / ScreenPix / Sony
  { name: 'MGM+', terms: ['MGM+', 'MGM PLUS'] },
  { name: 'MGM+ HITS', terms: ['MGM+ HITS', 'MGM HITS'] },
  { name: 'MGM+ MARQUEE', terms: ['MGM+ MARQUEE', 'MGM MARQUEE'] },
  { name: 'MGM+ DRIVE-IN', terms: ['MGM+ DRIVE-IN', 'MGM DRIVE-IN'] },
  { name: 'MGM HORROR', terms: ['MGM HORROR'] },

  { name: 'MOVIEPLEX', terms: ['MOVIEPLEX', 'MOVIE PLEX'] },
  { name: 'INDIEPLEX', terms: ['INDIEPLEX', 'INDIE PLEX'] },
  { name: 'RETROPLEX', terms: ['RETROPLEX', 'RETRO PLEX'] },

  { name: 'SCREENPIX', terms: ['SCREENPIX'] },
  { name: 'SCREENPIX ACTION', terms: ['SCREENPIX ACTION'] },
  { name: 'SCREENPIX VOICES', terms: ['SCREENPIX VOICES'] },
  { name: 'SCREENPIX WESTERNS', terms: ['SCREENPIX WESTERNS'] },

  { name: 'SONY MOVIES', terms: ['SONY MOVIES', 'SONY MOVIE', 'SONY'] }
]

function xmlEscape(value = '') {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

function xmltvId(name) {
  return name
    .replace(/&/g, 'And')
    .replace(/\+/g, 'Plus')
    .replace(/[^A-Za-z0-9]+/g, '.')
    .replace(/^\.+|\.+$/g, '')
    .toUpperCase() + '.us'
}

function normalize(value = '') {
  return String(value)
    .toUpperCase()
    .replace(/&AMP;/g, '&')
    .replace(/×/g, 'X')
    .replace(/\+/g, ' PLUS ')
    .replace(/[^A-Z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

async function fetchLineup() {
  const now = Math.floor(Date.now() / 1000)
  const url = `${BASE}/${PROVIDER_ID}/web?start=${now}&duration=1440`

  console.log(`[fetch] ${url}`)

  const res = await fetch(url, {
    headers: {
      accept: 'application/json',
      referer: 'https://www.tvguide.com/',
      'user-agent': 'Mozilla/5.0'
    }
  })

  if (!res.ok) {
    throw new Error(`TVGuide request failed: ${res.status} ${res.statusText}`)
  }

  const json = await res.json()
  return json?.data?.items || []
}

function channelSearchText(ch) {
  return normalize([
    ch.fullName,
    ch.name,
    ch.networkName,
    ch.number,
    ch.sourceId
  ].filter(Boolean).join(' '))
}

function findMatches(items) {
  const found = []
  const seen = new Set()

  for (const wanted of WANTED) {
    const matches = []

    for (const item of items) {
      const ch = item.channel
      if (!ch?.sourceId) continue

      const haystack = channelSearchText(ch)

      const matched = wanted.terms.some(term => {
        const needle = normalize(term)
        return haystack.includes(needle)
      })

      if (!matched) continue

      const key = `${wanted.name}|${ch.sourceId}`
      if (seen.has(key)) continue
      seen.add(key)

      matches.push({
        wantedName: wanted.name,
        sourceId: String(ch.sourceId),
        rawName: ch.fullName || ch.name || wanted.name,
        callName: ch.name || '',
        networkName: ch.networkName || '',
        number: ch.number || ''
      })
    }

    if (matches.length) {
      found.push(...matches)
    } else {
      console.log(`[missing] ${wanted.name}`)
    }
  }

  return found
}

function buildChannelsXml(matches) {
  const lines = []

  lines.push('<?xml version="1.0" encoding="UTF-8"?>')
  lines.push('<channels>')

  for (const m of matches.sort((a, b) => a.wantedName.localeCompare(b.wantedName))) {
    lines.push(
      `  <channel site="tvguide.com" lang="en" xmltv_id="${xmlEscape(xmltvId(m.wantedName))}" site_id="${PROVIDER_ID}#${xmlEscape(m.sourceId)}">${xmlEscape(m.wantedName)}</channel>`
    )
    lines.push(`  <!-- TVGuide raw: ${xmlEscape(m.rawName)}${m.number ? ` | ${xmlEscape(m.number)}` : ''} -->`)
  }

  lines.push('</channels>')
  return lines.join('\n') + '\n'
}

async function main() {
  fs.mkdirSync('channels', { recursive: true })

  const items = await fetchLineup()
  console.log(`[info] lineup channels returned: ${items.length}`)

  const matches = findMatches(items)

  fs.writeFileSync(OUTPUT, buildChannelsXml(matches))

  console.log(`[done] wrote ${OUTPUT}`)
  console.log(`[done] candidate matches: ${matches.length}`)
}

main().catch(err => {
  console.error(err)
  process.exit(1)
})
