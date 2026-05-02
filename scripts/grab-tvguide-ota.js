const fs = require('fs')

const PROVIDER_ID = process.env.TVGUIDE_PROVIDER_ID || '9100000664'
const OUTPUT = process.env.OUTPUT || 'guides/tvguide.xml'
const DAYS = Number(process.env.DAYS || 14)

const BASE = 'https://backend.tvguide.com/tvschedules/tvguide'

/*
  ONLY channels you actually want from your master list
  Boston locals intentionally excluded
*/
const CHANNEL_MAP = {
  // Portland locals
  '9233006796': 'NBC PORTLAND',
  '9200014312': 'ABC PORTLAND',
  '9233001666': 'CBS PORTLAND',
  '9233003676': 'FOX PORTLAND',

  // CW (only one you actually need)
  '9200006484': 'CW BOSTON',

  // OTA channels that exist in your master list
  '9200005724': 'COMET',
  '9266073627': 'LAFF',
  '9200016252': 'METV',
  '9233003377': 'GRIT',
  '9200020338': 'HEROES & ICONS',
  '9233005846': 'COURT TV',
  '9200017556': 'ION MYSTERY'
}

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

      const rawId = String(ch.sourceId)

      // 🔥 FILTER — ONLY KEEP CHANNELS IN YOUR MAP
      if (!CHANNEL_MAP[rawId]) continue

      const mappedId = CHANNEL_MAP[rawId]

      channels.set(mappedId, {
        id: mappedId,
        name: mappedId
      })

      for (const p of item.programSchedules || []) {
        if (!p.startTime || !p.endTime) continue

        if (p.endTime <= dayStart) continue
        if (p.startTime >= dayEnd) continue

        const key = `${mappedId}|${p.startTime}|${p.endTime}|${p.programId || ''}`

        programmes.set(key, {
          channelId: mappedId,
          start: Math.max(p.startTime, dayStart),
          stop: Math.min(p.endTime, dayEnd),
          title: p.title || 'Unknown'
        })
      }
    }

    // Logging per day
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

  // Build XML
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
