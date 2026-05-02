const fs = require('fs')

const PROVIDER_ID = process.env.TVGUIDE_PROVIDER_ID || '9100000664'
const OUTPUT = process.env.OUTPUT || 'guides/OTALocalsguide.xml'
const DAYS = Number(process.env.DAYS || 14)

const BASE = 'https://backend.tvguide.com/tvschedules/tvguide'

// Curated OTA list only.
// Boston locals are skipped.
const CHANNEL_MAP = {
  '9233006796': 'NBC PORTLAND',
  '9200014312': 'ABC PORTLAND',
  '9233001666': 'CBS PORTLAND',
  '9233003676': 'FOX PORTLAND',

  '9200006484': 'CW BOSTON',

  '9200005724': 'COMET',
  '9266073627': 'LAFF',
  '9200016252': 'METV',
  '9233003377': 'GRIT',
  '9200020338': 'HEROES & ICONS',
  '9233005846': 'COURT TV',
  '9200017556': 'ION MYSTERY'
}

function xmlEscape(value = '') {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
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
  const date = new Date(startEpoch * 1000).toISOString().slice(0, 10)
  const url = `${BASE}/${PROVIDER_ID}/web?start=${startEpoch}&duration=1440`

  console.log(`[fetch-day] ${date}`)

  const res = await fetch(url, {
    headers: {
      accept: 'application/json',
      referer: 'https://www.tvguide.com/',
      'user-agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'
    }
  })

  if (!res.ok) {
    throw new Error(`TVGuide request failed: ${res.status} ${res.statusText}`)
  }

  return res.json()
}

function getItems(json) {
  if (Array.isArray(json?.data?.items)) return json.data.items
  if (Array.isArray(json?.items)) return json.items
  return []
}

async function main() {
  fs.mkdirSync('guides', { recursive: true })

  const baseStart = startOfTodayEpoch()
  const channels = new Map()
  const allProgrammes = []

  console.log('[info] starting curated OTA locals guide')
  console.log(`[info] provider ID: ${PROVIDER_ID}`)
  console.log(`[info] days: ${DAYS}`)
  console.log(`[info] output: ${OUTPUT}`)

  for (let d = 0; d < DAYS; d++) {
    const dayStart = baseStart + d * 86400
    const dayEnd = dayStart + 86400
    const date = new Date(dayStart * 1000).toISOString().slice(0, 10)

    const json = await fetchDay(dayStart)
    const items = getItems(json)
    const dayProgrammes = new Map()

    for (const item of items) {
      const rawChannel = item.channel
      if (!rawChannel?.sourceId) continue

      const rawId = String(rawChannel.sourceId)
      const mappedId = CHANNEL_MAP[rawId]

      if (!mappedId) continue

      channels.set(mappedId, {
        id: mappedId,
        name: mappedId
      })

      const schedules = Array.isArray(item.programSchedules)
        ? item.programSchedules
        : []

      for (const p of schedules) {
        if (!p.startTime || !p.endTime) continue

        if (p.endTime <= dayStart) continue
        if (p.startTime >= dayEnd) continue

        const start = Math.max(p.startTime, dayStart)
        const stop = Math.min(p.endTime, dayEnd)

        if (stop <= start) continue

        const key = [
          mappedId,
          p.startTime,
          p.endTime,
          p.programId || '',
          p.title || ''
        ].join('|')

        dayProgrammes.set(key, {
          channelId: mappedId,
          start,
          stop,
          title: p.title || 'Unknown',
          subTitle: p.episodeTitle || p.subtitle || '',
          desc: p.description || p.shortDescription || '',
          category: p.catName || '',
          rating: p.rating || ''
        })
      }
    }

    console.log(`\n=== ${date} curated OTA totals ===`)

    const counts = {}
    for (const p of dayProgrammes.values()) {
      counts[p.channelId] = (counts[p.channelId] || 0) + 1
    }

    for (const channelName of Object.values(CHANNEL_MAP)) {
      if (counts[channelName]) {
        console.log(`${channelName} → ${counts[channelName]}`)
      }
    }

    allProgrammes.push(...dayProgrammes.values())
  }

  if (!channels.size) {
    throw new Error('No curated OTA channels found')
  }

  const sortedChannels = [...channels.values()].sort((a, b) =>
    a.id.localeCompare(b.id)
  )

  const sortedProgrammes = allProgrammes.sort((a, b) => {
    if (a.start !== b.start) return a.start - b.start
    return a.channelId.localeCompare(b.channelId)
  })

  const lines = []

  lines.push('<?xml version="1.0" encoding="UTF-8"?>')
  lines.push('<tv generator-info-name="festy1986 OTA Locals">')

  for (const ch of sortedChannels) {
    lines.push(`  <channel id="${xmlEscape(ch.id)}">`)
    lines.push(`    <display-name>${xmlEscape(ch.name)}</display-name>`)
    lines.push('  </channel>')
  }

  for (const p of sortedProgrammes) {
    lines.push(
      `  <programme start="${xmltvTime(p.start)}" stop="${xmltvTime(p.stop)}" channel="${xmlEscape(p.channelId)}">`
    )
    lines.push(`    <title lang="en">${xmlEscape(p.title)}</title>`)

    if (p.subTitle) {
      lines.push(`    <sub-title lang="en">${xmlEscape(p.subTitle)}</sub-title>`)
    }

    if (p.desc) {
      lines.push(`    <desc lang="en">${xmlEscape(p.desc)}</desc>`)
    }

    if (p.category) {
      lines.push(`    <category lang="en">${xmlEscape(p.category)}</category>`)
    }

    if (p.rating) {
      lines.push('    <rating>')
      lines.push(`      <value>${xmlEscape(p.rating)}</value>`)
      lines.push('    </rating>')
    }

    lines.push('  </programme>')
  }

  lines.push('</tv>')

  fs.writeFileSync(OUTPUT, lines.join('\n') + '\n')

  console.log(`\n[info] curated OTA channels: ${channels.size}`)
  console.log(`[info] curated OTA programmes: ${sortedProgrammes.length}`)
  console.log(`[done] wrote ${OUTPUT}`)
}

main().catch(err => {
  console.error(err)
  process.exit(1)
})
