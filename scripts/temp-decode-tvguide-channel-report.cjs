const fs = require('fs')

const inputFile = 'guides/tvguide.channel-id-report.txt'
const outputFile = 'guides/tvguide.decoded-channel-groups.txt'

if (!fs.existsSync(inputFile)) {
  console.error(`Missing ${inputFile}`)
  process.exit(1)
}

const text = fs.readFileSync(inputFile, 'utf8')

const blocks = text
  .split('============================================================')
  .map(x => x.trim())
  .filter(x => x.includes('SITE ID:'))

const rows = blocks.map(block => {
  const rawDisplay = getLine(block, 'RAW DISPLAY:')
  const rawXmltv = getLine(block, 'RAW XMLTV:')
  const siteId = getLine(block, 'SITE ID:')
  const apiName = getLine(block, 'API NAME:')
  const programs = getLine(block, 'PROGRAMS:')
  const samples = getSamples(block)

  return {
    rawDisplay,
    rawXmltv,
    siteId,
    apiName,
    programs,
    samples,
    guess: guessChannel(rawDisplay, rawXmltv, apiName, samples)
  }
})

const groups = new Map()

for (const row of rows) {
  const key = normalizeGroupKey(row.rawDisplay)
  if (!groups.has(key)) groups.set(key, [])
  groups.get(key).push(row)
}

const interesting = [...groups.entries()]
  .filter(([key, list]) => {
    if (list.length > 1) return true
    const joined = list.map(x => `${x.rawDisplay} ${x.rawXmltv} ${x.apiName}`).join(' ').toUpperCase()
    return [
      'ESPN', 'CBS', 'SHO', 'HBO', 'MAX', 'FX', 'LIFE', 'MTV',
      'CNN', 'CNBC', 'BBC', 'USA', 'TMC', 'STARZ', 'ENCORE',
      'TRAVEL', 'WEATH', 'PARAM', 'IFC', 'FUSE', 'REELZ', 'VICE',
      'TCM', 'OVAT', 'INSP', 'AWE'
    ].some(term => joined.includes(term))
  })
  .sort(([aKey, aList], [bKey, bList]) => {
    if (bList.length !== aList.length) return bList.length - aList.length
    return aKey.localeCompare(bKey)
  })

const out = []

out.push('TVGuide decoded channel groups')
out.push(`Input: ${inputFile}`)
out.push(`Blocks read: ${rows.length}`)
out.push(`Generated: ${new Date().toISOString()}`)
out.push('')
out.push('Purpose:')
out.push('- Groups duplicate or confusing TVGuide raw names.')
out.push('- Uses API NAME and schedule samples to help identify the real channel behind each site_id.')
out.push('- This does NOT rewrite your guide yet.')
out.push('')

for (const [key, list] of interesting) {
  out.push('============================================================')
  out.push(`GROUP: ${key}`)
  out.push(`COUNT: ${list.length}`)
  out.push('')

  for (const row of list) {
    out.push(`SITE ID:     ${row.siteId}`)
    out.push(`RAW DISPLAY: ${row.rawDisplay}`)
    out.push(`RAW XMLTV:   ${row.rawXmltv}`)
    out.push(`API NAME:    ${row.apiName}`)
    out.push(`PROGRAMS:    ${row.programs}`)
    out.push(`GUESS:       ${row.guess}`)
    out.push('SAMPLES:')
    for (const s of row.samples.slice(0, 8)) {
      out.push(`- ${s}`)
    }
    out.push('')
  }
}

const forcedCandidates = rows
  .filter(r => r.guess && !r.guess.startsWith('UNKNOWN'))
  .sort((a, b) => a.guess.localeCompare(b.guess))

out.push('')
out.push('============================================================')
out.push('POSSIBLE FORCED MAP CANDIDATES')
out.push('============================================================')
out.push('')
out.push('Copy only the ones you trust into the real builder later.')
out.push('')

for (const r of forcedCandidates) {
  out.push(`'${r.guess}': '${r.siteId}', // raw=${r.rawDisplay} api=${r.apiName}`)
}

fs.writeFileSync(outputFile, out.join('\n'))
console.log(`[done] wrote ${outputFile}`)

function getLine(block, prefix) {
  const line = block.split('\n').find(l => l.trim().startsWith(prefix))
  return line ? line.replace(prefix, '').trim() : ''
}

function getSamples(block) {
  const lines = block.split('\n')
  const idx = lines.findIndex(l => l.trim() === 'SAMPLES:')
  if (idx < 0) return []
  return lines
    .slice(idx + 1)
    .filter(l => l.trim().startsWith('- '))
    .map(l => l.trim().replace(/^- /, '').trim())
}

function normalizeGroupKey(value) {
  return String(value || '')
    .replace(/\.us$/i, '')
    .trim()
    .toUpperCase()
}

function haystack(rawDisplay, rawXmltv, apiName, samples) {
  return `${rawDisplay} ${rawXmltv} ${apiName} ${samples.join(' ')}`.toUpperCase()
}

function guessChannel(rawDisplay, rawXmltv, apiName, samples) {
  const h = haystack(rawDisplay, rawXmltv, apiName, samples)

  const rules = [
    ['ESPN NEWS', ['ESPNNEWHD', 'ESPNEWS']],
    ['ESPN2', ['ESPN2', 'ESPN 2']],
    ['ESPN', ['ESPNHD', 'SPORTSCENTER', 'NFL LIVE', 'COLLEGE GAMEDAY']],
    ['CBS SPORTS NETWORK', ['CBSSPTHD', 'CBS SPORTS NETWORK']],
    ['CBS SPORTS HQ', ['CBS SPORTS HQ']],
    ['USA NETWORK', ['USAHD', 'USA-E', 'USA NETWORK']],
    ['FXX', ['FXXHD', 'FXX']],
    ['FX MOVIE CHANNEL', ['FXMHD', 'FXM']],
    ['PARAMOUNT NETWORK', ['PARMT', 'PARAMOUNT NETWORK']],
    ['IFC', ['IFCHD', 'IFC']],
    ['BBC AMERICA', ['BBCAMHD', 'BBCAME']],
    ['VICE', ['VICEHD', 'VICE']],
    ['REELZ', ['REELZHD', 'REELZ']],
    ['FUSE', ['FUSEHD', 'FUSE']],
    ['TRAVEL CHANNEL', ['TRAVELHD', 'TRAVEL']],
    ['THE WEATHER CHANNEL', ['WEATHHD', 'WEATHER CHANNEL']],
    ['LIFETIME', ['LIFEHD', 'LIFETIME']],
    ['LMN', ['LMNHD', 'LMN']],
    ['MTV2', ['MTV2HD', 'MTV2']],
    ['CMT', ['CMTHD', 'CMTV']],
    ['AWE', ['AWE']],
    ['OVATION', ['OVATHD', 'OVATION']],
    ['TCM', ['TCMHD', 'TURNER CLASSIC']],
    ['INSP', ['INSPHD', 'INSP']],
    ['HBO', ['HBOHD']],
    ['HBO HITS', ['HBO2HD', 'HBO HITS']],
    ['HBO DRAMA', ['HBOSIGHD', 'HBO DRAMA']],
    ['HBO COMEDY', ['HBOCOMHD', 'HBO COMEDY']],
    ['CINEMAX', ['MAXHD']],
    ['CINEMAX HITS', ['MOREMAXHD']],
    ['CINEMAX ACTION', ['ACTMAXHD']],
    ['CINEMAX CLASSICS', ['5STARMAXHD']],
    ['PARAMOUNT+ WITH SHOWTIME', ['SHOHD']],
    ['SHOXBET', ['SHOXBET', 'SHOBET', 'SHOWTIME BET']],
    ['SHOWTIME 2', ['SHO2XEHD', 'SHO2']],
    ['SHOWTIME EXTREME', ['SHOWEXHD']],
    ['SHOWTIME FAMILY ZONE', ['SHOWFAM']],
    ['SHOWTIME NEXT', ['SHOWNEXT']],
    ['SHOWTIME WOMEN', ['SHOWWOM']],
    ['SHOWTIME SHOWCASE', ['SHWCASEHD']],
    ['THE MOVIE CHANNEL', ['TMCHD', 'TMC']],
    ['TMC XTRA', ['TMCXTRAHD']],
    ['STARZ', ['STARZHD']],
    ['STARZ EDGE', ['STARZEDHD']],
    ['STARZ CINEMA', ['STARZCINHD']],
    ['STARZ COMEDY', ['STARZCOMHD']],
    ['STARZ ENCORE', ['ENCOREHD']],
    ['STARZ ENCORE ACTION', ['ENCRACTHD']],
    ['STARZ ENCORE BLACK', ['ENCRBLHD']],
    ['STARZ ENCORE CLASSIC', ['ENCRCLHD']],
    ['STARZ ENCORE SUSPENSE', ['ENCORSHD']],
    ['STARZ ENCORE FAMILY', ['ENCORFM']],
    ['STARZ KIDS & FAMILY', ['STARZFAMHD']],
    ['STARZ INBLACK', ['STARZBLKHD']],
    ['MGM+', ['MGM+']],
    ['MGM+ HITS', ['MGM+HIT']],
    ['MGM+ MARQUEE', ['MGM+MAR']],
    ['MGM+ DRIVE-IN', ['MGM+DRV']],
    ['MOVIEPLEX', ['PLEXHD']],
    ['INDIEPLEX', ['INDIPX']]
  ]

  for (const [name, needles] of rules) {
    if (needles.some(n => h.includes(n.toUpperCase()))) return name
  }

  return `UNKNOWN (${apiName || rawDisplay || rawXmltv})`
}
