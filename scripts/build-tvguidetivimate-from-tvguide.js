const fs = require('fs')
const path = require('path')

const INPUT = 'guides/tvguide.xml'
const OUTPUT = 'guides/tvguidetivimate.xml'

const MASTER = [
  ['ESPN 2', '9200012351'],
  ['CBS SPORTS NETWORK', '9233015468'],

  ['FXX', '9200014910'],
  ['FXM', '9200001026'],
  ['TRAVEL CHANNEL', '9233008142'],
  ['THE WEATHER CHANNEL', '9200016258'],
  ['MTV 2', '9200012265'],
  ['LMN', '9233009429'],
  ['ION PLUS', '9200008618'],
  ['AWE', '9200020638'],

  ['HBO HITS', '9233013492'],
  ['HBO DRAMA', '9200002532'],
  ['HBO COMEDY', '9233003785'],

  ['CINEMAX', '9200000143'],
  ['CINEMAX HITS', '9200006529'],
  ['CINEMAX ACTION', '9233006971'],
  ['CINEMAX CLASSICS', '9233006977'],

  ['PARAMOUNT+ WITH SHOWTIME', '9233011188'],
  ['SHOWTIME 2', '9200014450'],
  ['SHOWTIME EXTREME', '9233015495'],
  ['SHOWTIME FAMILY ZONE', '9200000968'],
  ['SHOWTIME NEXT', '9200016686'],
  ['SHOWTIME WOMEN', '9200002975'],
  ['SHOWTIME SHOWCASE', '9233003805'],

  ['THE MOVIE CHANNEL', '9233013260'],
  ['TMC XTRA', '9200009198'],

  ['STARZ EDGE', '9233003754'],
  ['STARZ CINEMA', '9200009352'],
  ['STARZ COMEDY', '9233001912'],
  ['STARZ KIDS & FAMILY', '9200020089'],

  ['MGM+ HITS', '9233013634'],
  ['MGM+ MARQUEE', '9200020594'],
  ['MGM+ DRIVE-IN', '9200006851']
]

function escapeXml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

if (!fs.existsSync(INPUT)) {
  console.error(`Missing input: ${INPUT}`)
  process.exit(1)
}

const xml = fs.readFileSync(INPUT, 'utf8')

const selected = []

for (const [name, id] of MASTER) {
  const hasId =
    xml.includes(`id="${id}"`) ||
    xml.includes(`#${id}"`) ||
    xml.includes(`#${id}`)

  if (!hasId) {
    console.log(`[missing from raw] ${name} (${id})`)
    continue
  }

  selected.push({ name, id })
  console.log(`[forced] ${name} (${id})`)
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
    `  <channel id="${escapeXml(ch.id)}">\n    <display-name>${escapeXml(ch.name)}</display-name>\n  </channel>`
  ),
  ...keptProgrammes.map(p => p.replace(/^/gm, '  ')),
  '</tv>',
  ''
].join('\n')

fs.mkdirSync(path.dirname(OUTPUT), { recursive: true })
fs.writeFileSync(OUTPUT, output)

console.log(`Forced ${selected.length}/${MASTER.length} missing channels.`)
console.log(`Copied ${keptProgrammes.length} programme entries.`)
console.log(`Wrote ${OUTPUT}`)
