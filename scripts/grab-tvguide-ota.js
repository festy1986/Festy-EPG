const fs = require('fs')

const PROVIDER_ID = process.env.TVGUIDE_PROVIDER_ID || '9100000664'
const OUTPUT = process.env.OUTPUT || 'guides/OTALocalsguide.xml'
const DAYS = Number(process.env.DAYS || 14)

const BASE = 'https://backend.tvguide.com/tvschedules/tvguide'

function xmlEscape(v = '') {
  return String(v)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function xmltvTime(unix) {
  const d = new Date(unix * 1000)
  const pad = n => String(n).padStart(2, '0')

  return (
    d.getUTCFullYear() +
    pad(d.getUTCMonth() + 1) +
    pad(d.getUTCDate()) +
    pad(d.getUTCHours()) +
    pad(d.getUTCMinutes()) +
    pad(d.getUTCSeconds()) +
    ' +0000'
  )
}

function startOfTodayEpoch() {
  const now = new Date()
  return Math.floor(
    new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime() / 1000
  )
}

/* 🔥 AUTO NAME CLEANER */
function cleanName(channel) {
  const full = channel.fullName || ''
  const network = channel.networkName || ''

  // If network exists → use it (best case)
  if (network && network.length > 1) {
    if (network === 'NBC') return 'NBC PORTLAND'
    if (network === 'ABC') return 'ABC PORTLAND'
    if (network === 'CBS') return 'CBS PORTLAND'
    if (network === 'FOX') return 'FOX PORTLAND'
    if (network === 'CW') return 'CW BOSTON'
    return network.toUpperCase()
  }

  // fallback: extract from parentheses
  const match = full.match(/\((.*?)\)/)
  if (match) return match[1].toUpperCase()

  return full.toUpperCase()
}

async function fetchDay(startEpoch) {
  const url = `${BASE}/${PROVIDER_ID}/web?start=${startEpoch}&duration=1440`

  console.log(`[fetch-day] ${new Date(startEpoch * 1000).toISOString().slice(0,10)}`)

  const res = await fetch(url, {
    headers: {
      accept: 'application/json',
      referer: 'https://www.tvguide.com/',
      'user-agent': 'Mozilla/5.0'
    }
  })

  if (!res.ok) throw new Error(`TVGuide request failed`)

  return res.json()
}

function getItems(json) {
  return json?.data?.items || []
}

async function main() {
  fs.mkdirSync('guides', { recursive: true })

  const baseStart = startOfTodayEpoch()
  const channels = new Map()
  const allProgrammes = []

  for (let d = 0; d < DAYS; d++) {
    const dayStart = baseStart + d * 86400
    const dayEnd = dayStart + 86400

    const json = await fetchDay(dayStart)
    const items = getItems(json)

    const programmes = new Map()

    for (const item of items) {
      const ch = item.channel
      if (!ch?.sourceId) continue

      const id = String(ch.sourceId)
      const name = cleanName(ch)

      channels.set(name, { id: name, name })

      for (const p of item.programSchedules || []) {
        if (!p.startTime || !p.endTime) continue
        if (p.endTime <= dayStart) continue
        if (p.startTime >= dayEnd) continue

        const key = `${name}|${p.startTime}|${p.endTime}`

        programmes.set(key, {
          channelId: name,
          start: Math.max(p.startTime, dayStart),
          stop: Math.min(p.endTime, dayEnd),
          title: p.title || 'Unknown'
        })
      }
    }

    console.log(`\n=== ${new Date(dayStart * 1000).toISOString().slice(0,10)} ===`)

    const counts = {}
    for (const p of programmes.values()) {
      counts[p.channelId] = (counts[p.channelId] || 0) + 1
    }

    for (const [ch, count] of Object.entries(counts)) {
      console.log(`${ch} → ${count}`)
    }

    allProgrammes.push(...programmes.values())
  }

  const lines = []
  lines.push('<?xml version="1.0" encoding="UTF-8"?>')
  lines.push('<tv>')

  for (const ch of channels.values()) {
    lines.push(`  <channel id="${xmlEscape(ch.id)}">`)
    lines.push(`    <display-name>${xmlEscape(ch.name)}</display-name>`)
    lines.push('  </channel>')
  }

  for (const p of allProgrammes.sort((a,b)=>a.start-b.start)) {
    lines.push(
      `  <programme start="${xmltvTime(p.start)}" stop="${xmltvTime(p.stop)}" channel="${p.channelId}">`
    )
    lines.push(`    <title>${xmlEscape(p.title)}</title>`)
    lines.push('  </programme>')
  }

  lines.push('</tv>')

  fs.writeFileSync(OUTPUT, lines.join('\n'))

  console.log(`\n[done] wrote ${OUTPUT}`)
}

main().catch(err => {
  console.error(err)
  process.exit(1)
})
