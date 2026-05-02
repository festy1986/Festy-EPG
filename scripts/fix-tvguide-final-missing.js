const fs = require('fs')

const file = process.argv[2] || 'sites/tvguide-test.com/tvguide-test.com.channels.xml'

if (!fs.existsSync(file)) {
  console.error(`Missing file: ${file}`)
  process.exit(1)
}

let xml = fs.readFileSync(file, 'utf8')

const fixes = [
  {
    wanted: ['GRIT'],
    aliases: ['GRIT', 'Grit', 'Grit TV', 'WIPL-DT4'],
    xmltv: 'Grit.us',
    name: 'Grit'
  },
  {
    wanted: ['ION PLUS', 'IONPLUS'],
    aliases: ['ION PLUS', 'IONPlus', 'Ion Plus', 'ION Mystery Plus', 'WIPL-DT5'],
    xmltv: 'IONPlus.us',
    name: 'ION Plus'
  },
  {
    wanted: ['COURT TV', 'COURTTV'],
    aliases: ['COURT TV', 'CourtTV', 'Court TV', 'WIPL-DT2'],
    xmltv: 'CourtTV.us',
    name: 'Court TV'
  },
  {
    wanted: ['ANTENNA TV', 'ANTENNA'],
    aliases: ['ANTENNA TV', 'Antenna', 'Antenna TV', 'WPFO-DT4'],
    xmltv: 'AntennaTV.us',
    name: 'Antenna TV'
  },
  {
    wanted: ['COZI TV', 'COZI'],
    aliases: ['COZI TV', 'Cozi', 'Cozi TV', 'WCSH-DT', 'WLBZ-DT'],
    xmltv: 'CoziTV.us',
    name: 'Cozi TV'
  },
  {
    wanted: ['HALLMARK DRAMA', 'HALLMARK FAMILY'],
    aliases: ['HALLMARK FAMILY', 'Hallmark Family', 'Hallmark Drama'],
    xmltv: 'HallmarkFamily.us',
    name: 'Hallmark Family',
    forceSiteId: '9233010939'
  }
]

function norm(s) {
  return String(s || '')
    .replace(/&amp;/g, '&')
    .replace(/\s+/g, ' ')
    .trim()
    .toUpperCase()
}

function parseChannels(text) {
  const re = /<channel\b([^>]*)>([\s\S]*?)<\/channel>/g
  const out = []
  let m

  while ((m = re.exec(text))) {
    const attrs = m[1]
    const display = m[2].trim()
    const siteId = (attrs.match(/site_id="([^"]*)"/) || [])[1] || ''
    const xmltvId = (attrs.match(/xmltv_id="([^"]*)"/) || [])[1] || ''
    const lang = (attrs.match(/lang="([^"]*)"/) || [])[1] || 'en'

    out.push({
      full: m[0],
      attrs,
      display,
      siteId,
      xmltvId,
      lang,
      start: m.index,
      end: re.lastIndex
    })
  }

  return out
}

function makeChannel(siteId, xmltvId, name, lang = 'en') {
  return ` <channel site="tvguide.com" site_id="${siteId}" lang="${lang}" xmltv_id="${xmltvId}">${name}</channel>`
}

let channels = parseChannels(xml)
const report = []

for (const fix of fixes) {
  const wantedSet = new Set(fix.wanted.map(norm))
  const aliasSet = new Set(fix.aliases.map(norm))

  let target = channels.find(ch => wantedSet.has(norm(ch.display)) || wantedSet.has(norm(ch.xmltvId)))
  let source = null

  if (fix.forceSiteId) {
    source = {
      siteId: fix.forceSiteId,
      lang: 'en'
    }
  } else {
    source = channels.find(ch =>
      ch.siteId &&
      (
        aliasSet.has(norm(ch.display)) ||
        aliasSet.has(norm(ch.xmltvId)) ||
        fix.aliases.some(a => norm(ch.display).includes(norm(a))) ||
        fix.aliases.some(a => norm(ch.xmltvId).includes(norm(a)))
      )
    )
  }

  if (!source || !source.siteId) {
    report.push(`MISS: ${fix.name} - no usable TVGuide site_id found in this lineup`)
    continue
  }

  const newLine = makeChannel(source.siteId, fix.xmltv, fix.name, source.lang || 'en')

  if (target) {
    if (target.siteId === source.siteId && target.xmltvId === fix.xmltv && target.display === fix.name) {
      report.push(`OK: ${fix.name} already correct`)
      continue
    }

    xml = xml.replace(target.full, newLine)
    report.push(`FIXED: ${target.display} -> ${fix.name} | site_id=${source.siteId}`)
  } else {
    xml = xml.replace('</channels>', `${newLine}\n</channels>`)
    report.push(`ADDED: ${fix.name} | site_id=${source.siteId}`)
  }

  channels = parseChannels(xml)
}

fs.writeFileSync(file, xml)

console.log('\nFinal missing TVGuide cleanup report:')
console.log(report.join('\n'))
