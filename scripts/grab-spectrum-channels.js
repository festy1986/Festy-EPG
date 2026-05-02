const fs = require('fs')

const PROVIDER_ID = '9100002976'
const OUTPUT = 'channels/spectrum.channels.xml'

const URL = `https://backend.tvguide.com/tvschedules/tvguide/${PROVIDER_ID}/web?start=${Math.floor(Date.now()/1000)}&duration=1440`

async function main() {
  fs.mkdirSync('channels', { recursive: true })

  console.log('[fetching channels]')

  const res = await fetch(URL, {
    headers: {
      'User-Agent': 'Mozilla/5.0',
      'Referer': 'https://www.tvguide.com/'
    }
  })

  const json = await res.json()
  const items = json?.data?.items || []

  const channels = new Map()

  for (const item of items) {
    const ch = item.channel
    if (!ch?.sourceId) continue

    const id = `${PROVIDER_ID}#${ch.sourceId}`

    const name =
      ch.networkName ||
      ch.name ||
      ch.fullName ||
      `Channel ${ch.sourceId}`

    channels.set(id, {
      id,
      name
    })
  }

  const lines = []
  lines.push('<?xml version="1.0" encoding="UTF-8"?>')
  lines.push('<channels>')

  for (const ch of [...channels.values()].sort((a, b) =>
    a.name.localeCompare(b.name)
  )) {
    lines.push(
      `  <channel site="tvguide.com" lang="en" xmltv_id="${ch.name}.us" site_id="${ch.id}">${ch.name}</channel>`
    )
  }

  lines.push('</channels>')

  fs.writeFileSync(OUTPUT, lines.join('\n'))

  console.log(`[done] channels found: ${channels.size}`)
  console.log(`[done] saved to ${OUTPUT}`)
}

main()
