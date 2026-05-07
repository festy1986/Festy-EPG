const fs = require('fs')

const guidePath = process.argv[2] || 'guides/tvguidetivimateguide.xml'

if (!fs.existsSync(guidePath)) {
  console.error(`Missing ${guidePath}`)
  process.exit(1)
}

const logoBase = 'https://raw.githubusercontent.com/festy1986/festy-epg/main/logos/'

const logoFixes = {
  'FS1.us': `${logoBase}FOX%20Sports%201%20HD.png`,
  'FS2.us': `${logoBase}FOX%20Sports%202.png`,
  'DISCOVERY.SCIENCE.us': `${logoBase}Science%20HD.png`,
  'SMITHSONIAN.CHANNEL.us': `${logoBase}smithsonian%20channel%20extra.png`,
  'LMN.us': `${logoBase}lifetime%20movie%20network.png`,
  'POP.us': `${logoBase}Pop%20Network%20HD.png`,
  'VICE.us': `${logoBase}Vice_TV.webp`,
  'CRIME.AND.INVESTIGATION.us': `${logoBase}Crime%20%26%20Investigation%20Network%20HD.png`,
  'HALLMARK.DRAMA.us': `${logoBase}Hallmark%20Family.png`,
  'CINEMAX.ACTION.us': `${logoBase}Cinemax_Action_2025.svg`,
  'NESN.us': `${logoBase}New%20England%20Sports%20Network.png`,
  'NESN.PLUS.us': `${logoBase}New%20England%20Sports%20Network%20Plus%20HD.png`,
  'NECN.us': `${logoBase}New%20England%20Cable%20News.png`
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function escapeXml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function upsertIcon(channelBlock, logoUrl) {
  const icon = `<icon src="${escapeXml(logoUrl)}"/>`

  // Overwrite any existing icon, including old Imgur icons.
  if (/<icon\b[^>]*\/?>/i.test(channelBlock)) {
    return channelBlock.replace(/<icon\b[^>]*\/?>/i, icon)
  }

  // Add icon after display-name when missing.
  if (/<display-name\b[^>]*>[\s\S]*?<\/display-name>/i.test(channelBlock)) {
    return channelBlock.replace(
      /(<display-name\b[^>]*>[\s\S]*?<\/display-name>)/i,
      `$1${icon}`
    )
  }

  return channelBlock.replace(/(<channel\b[^>]*>)/i, `$1${icon}`)
}

let xml = fs.readFileSync(guidePath, 'utf8')
let fixed = 0
const missing = []

for (const [id, logoUrl] of Object.entries(logoFixes)) {
  const re = new RegExp(
    `<channel\\b([^>]*)\\bid="${escapeRegExp(id)}"([^>]*)>[\\s\\S]*?<\\/channel>`,
    'i'
  )

  if (!re.test(xml)) {
    missing.push(id)
    continue
  }

  xml = xml.replace(re, block => {
    fixed++
    return upsertIcon(block, logoUrl)
  })
}

fs.writeFileSync(guidePath, xml)

console.log(`TiviMate logo fixes applied: ${fixed}`)

if (missing.length) {
  console.log('Channels not found:')
  missing.forEach(id => console.log(`- ${id}`))
}
