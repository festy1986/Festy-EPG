const fs = require('fs')

const repo = process.env.GITHUB_REPOSITORY || 'festy1986/festy-epg'
const branch = process.env.GITHUB_REF_NAME || 'main'

const LOGO_DIR = 'logos'

const DEFAULT_GUIDES = [
  'guides/tvguidetivimate.xml',
  'guides/OTALocalsguide.xml'
]

const guides = process.argv.slice(2).length
  ? process.argv.slice(2)
  : DEFAULT_GUIDES

function normalize(name) {
  return String(name || '')
    .toLowerCase()
    .replace(/&amp;/g, 'and')
    .replace(/&/g, 'and')
    .replace(/\+/g, 'plus')
    .replace(/\bhd\b/g, '')
    .replace(/\btv\b/g, '')
    .replace(/\bchannel\b/g, '')
    .replace(/[^a-z0-9]/g, '')
}

function logoUrl(file) {
  return `https://raw.githubusercontent.com/${repo}/${branch}/${LOGO_DIR}/${encodeURIComponent(file)}`
}

function loadLogos() {
  if (!fs.existsSync(LOGO_DIR)) {
    console.error(`Missing folder: ${LOGO_DIR}`)
    process.exit(1)
  }

  const logos = new Map()

  for (const file of fs.readdirSync(LOGO_DIR)) {
    if (!/\.(png|jpg|jpeg|webp)$/i.test(file)) continue

    const name = file.replace(/\.(png|jpg|jpeg|webp)$/i, '')
    logos.set(normalize(name), file)
  }

  return logos
}

const aliases = {
  'MS NOW': ['msnbc', 'ms now', 'msnow'],
  'ESPN2': ['espn 2', 'espn2'],
  'MTV2': ['mtv 2', 'mtv2'],
  'TRUTV': ['tru tv', 'trutv'],
  'AXS TV': ['axs', 'axs tv'],
  'FX MOVIE CHANNEL': ['fxm', 'fx movie channel'],
  'NEW ENGLAND CABLE NEWS': ['necn'],
  'NESN PLUS': ['nesn plus', 'nesn+', 'nesn plus hd'],
  'NBC SPORTS BOSTON': ['nbc sports boston', 'sports boston'],
  'GAME SHOW NETWORK': ['gsn'],
  'PARAMOUNT+ WITH SHOWTIME': ['paramount with showtime', 'showtime paramount'],
  'SHOXBET': ['shoxbet', 'showtime bet'],
  'MGM+': ['mgm plus', 'mgm'],
  'MGM+ HITS': ['mgm hits', 'mgm plus hits'],
  'MGM+ MARQUEE': ['mgm marquee', 'mgm plus marquee'],
  'MGM+ DRIVE-IN': ['mgm drive in', 'mgm plus drive in'],
  'STARZ INBLACK': ['starz in black', 'starz inblack'],
  'THE MOVIE CHANNEL': ['the movie channel', 'tmc'],
  'TMC XTRA': ['tmc xtra', 'the movie channel xtra']
}

function findLogo(channelName, logos) {
  const direct = logos.get(normalize(channelName))
  if (direct) return direct

  const aliasList = aliases[String(channelName).toUpperCase()] || []

  for (const alias of aliasList) {
    const found = logos.get(normalize(alias))
    if (found) return found
  }

  return null
}

function updateGuide(file, logos) {
  if (!fs.existsSync(file)) {
    console.log(`[skip] ${file} does not exist`)
    return
  }

  let xml = fs.readFileSync(file, 'utf8')
  let changed = 0
  const missing = new Set()

  xml = xml.replace(/<channel\b[\s\S]*?<\/channel>/gi, block => {
    const nameMatch = block.match(/<display-name[^>]*>([\s\S]*?)<\/display-name>/i)

    if (!nameMatch) return block

    const channelName = nameMatch[1]
      .replace(/<!\[CDATA\[/g, '')
      .replace(/\]\]>/g, '')
      .trim()

    const logo = findLogo(channelName, logos)

    if (!logo) {
      missing.add(channelName)
      return block
    }

    const icon = `<icon src="${logoUrl(logo)}"/>`

    let updated

    if (/<icon\b[^>]*\/>/i.test(block)) {
      updated = block.replace(/<icon\b[^>]*\/>/i, icon)
    } else {
      updated = block.replace(
        /(<display-name[^>]*>[\s\S]*?<\/display-name>)/i,
        `$1\n    ${icon}`
      )
    }

    if (updated !== block) changed++

    return updated
  })

  fs.writeFileSync(file, xml)

  console.log(`[done] ${file}`)
  console.log(`custom logos applied: ${changed}`)
  console.log(`missing logo matches: ${missing.size}`)

  for (const name of [...missing].sort()) {
    console.log(`- ${name}`)
  }
}

const logos = loadLogos()

for (const guide of guides) {
  updateGuide(guide, logos)
}
