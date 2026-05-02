const fs = require('fs')

const INPUT = process.env.INPUT || 'guides/tvguide.xml'
const OUTPUT = process.env.OUTPUT || INPUT

const REMOVE_CHANNELS = new Set([
  'ABC PORTLAND',
  'CBS PORTLAND',
  'FOX PORTLAND',
  'NBC PORTLAND',
  'CW BOSTON',

  'COMET',
  'LAFF',
  'METV',
  'GRIT',
  'HEROES & ICONS',
  'COURT TV',
  'ION MYSTERY',

  'ION PLUS',
  'ANTENNA TV',
  'PBS'
])

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function removeChannelBlock(xml, channelId) {
  const escaped = escapeRegex(channelId)

  return xml.replace(
    new RegExp(`\\s*<channel\\s+id=["']${escaped}["'][\\s\\S]*?<\\/channel>`, 'g'),
    ''
  )
}

function removeProgrammeBlocks(xml, channelId) {
  const escaped = escapeRegex(channelId)

  return xml.replace(
    new RegExp(`\\s*<programme\\b[^>]*\\bchannel=["']${escaped}["'][\\s\\S]*?<\\/programme>`, 'g'),
    ''
  )
}

function main() {
  if (!fs.existsSync(INPUT)) {
    throw new Error(`Missing Spectrum guide: ${INPUT}`)
  }

  let xml = fs.readFileSync(INPUT, 'utf8')

  const beforeChannels = (xml.match(/<channel\b/g) || []).length
  const beforeProgrammes = (xml.match(/<programme\b/g) || []).length

  for (const channelId of REMOVE_CHANNELS) {
    xml = removeChannelBlock(xml, channelId)
    xml = removeProgrammeBlocks(xml, channelId)
  }

  const afterChannels = (xml.match(/<channel\b/g) || []).length
  const afterProgrammes = (xml.match(/<programme\b/g) || []).length

  fs.writeFileSync(OUTPUT, xml.trim() + '\n')

  console.log(`[done] cleaned Spectrum guide: ${OUTPUT}`)
  console.log(`[info] channels: ${beforeChannels} -> ${afterChannels}`)
  console.log(`[info] programmes: ${beforeProgrammes} -> ${afterProgrammes}`)
}

main()
