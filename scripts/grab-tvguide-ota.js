const fs = require('fs')

const PROVIDER_ID = process.env.TVGUIDE_PROVIDER_ID || '9100000664'
const OUTPUT = process.env.OUTPUT || 'guides/tvguide.xml'
const DAYS = Number(process.env.DAYS || 1)
const CHUNK_MINUTES = Number(process.env.CHUNK_MINUTES || 120)

const BASE = 'https://backend.tvguide.com/tvschedules/tvguide'

function xmlEscape(value = '') {
  return String(value)
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
  return Math.floor(new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime() / 1000)
}

async function fetchChunk(startEpoch, duration) {
  const url = `${BASE}/${PROVIDER_ID}/web?start=${startEpoch}&duration=${duration}`
  console.log(`Fetching ${url}`)

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

  const channels = new Map()
  const programmes = new Map()

  const start = startOfTodayEpoch()
  const totalMinutes = DAYS * 24 * 60

  for (let offset = 0; offset < totalMinutes; offset += CHUNK_MINUTES) {
    const chunkStart = start + offset * 60
    const json = await fetchChunk(chunkStart, CHUNK_MINUTES)
    const items = getItems(json)

    if (!items.length) {
      console.log('No items found in this chunk')
      continue
    }

    for (const item of items) {
      const channel = item.channel
      if (!channel?.sourceId) continue

      const channelId = String(channel.sourceId)
      const displayName =
        channel.fullName ||
        channel.networkName ||
        channel.name ||
        `Channel ${channelId}`

      channels.set(channelId, {
        id: channelId,
        name: channel.name || displayName,
        fullName: displayName,
        number: channel.number || '',
        networkName: channel.networkName || '',
        logo: channel.logo || ''
      })

      const schedules = Array.isArray(item.programSchedules)
        ? item.programSchedules
        : []

      console.log(
        `[channel] ${displayName} | ${channel.number || 'no-number'} | ${channelId} | ${schedules.length} program(s)`
      )

      for (const p of schedules) {
        if (!p.startTime || !p.endTime) continue

        const key = `${channelId}|${p.startTime}|${p.endTime}|${p.programId || p.title || ''}`

        programmes.set(key, {
          channelId,
          start: p.startTime,
          stop: p.endTime,
          title: p.title || 'Unknown',
          subTitle: p.episodeTitle || '',
          desc: p.description || '',
          category: p.catName || '',
          rating: p.rating || ''
        })
      }
    }
  }

  if (!channels.size) {
    throw new Error('No channels found in TVGuide backend response')
  }

  console.log(`Found ${channels.size} channel(s)`)
  console.log(`Found ${programmes.size} programme(s)`)

  const lines = []
  lines.push('<?xml version="1.0" encoding="UTF-8"?>')
  lines.push('<tv generator-info-name="festy1986 TVGuide OTA">')

  for (const ch of [...channels.values()].sort((a, b) => {
    const an = parseFloat(a.number) || 9999
    const bn = parseFloat(b.number) || 9999
    return an - bn
  })) {
    lines.push(`  <channel id="${xmlEscape(ch.id)}">`)
    lines.push(`    <display-name>${xmlEscape(ch.fullName)}</display-name>`)
    if (ch.name && ch.name !== ch.fullName) {
      lines.push(`    <display-name>${xmlEscape(ch.name)}</display-name>`)
    }
    if (ch.number) {
      lines.push(`    <display-name>${xmlEscape(ch.number)}</display-name>`)
    }
    if (ch.logo) {
      const logoUrl = ch.logo.startsWith('http')
        ? ch.logo
        : `https://www.tvguide.com/a/img/catalog${ch.logo}`
      lines.push(`    <icon src="${xmlEscape(logoUrl)}" />`)
    }
    lines.push('  </channel>')
  }

  for (const p of [...programmes.values()].sort((a, b) => a.start - b.start)) {
    lines.push(
      `  <programme start="${xmltvTime(p.start)}" stop="${xmltvTime(p.stop)}" channel="${xmlEscape(p.channelId)}">`
    )
    lines.push(`    <title lang="en">${xmlEscape(p.title)}</title>`)
    if (p.subTitle) lines.push(`    <sub-title lang="en">${xmlEscape(p.subTitle)}</sub-title>`)
    if (p.desc) lines.push(`    <desc lang="en">${xmlEscape(p.desc)}</desc>`)
    if (p.category) lines.push(`    <category lang="en">${xmlEscape(p.category)}</category>`)
    if (p.rating) {
      lines.push('    <rating>')
      lines.push(`      <value>${xmlEscape(p.rating)}</value>`)
      lines.push('    </rating>')
    }
    lines.push('  </programme>')
  }

  lines.push('</tv>')

  fs.writeFileSync(OUTPUT, lines.join('\n') + '\n')
  console.log(`Wrote ${OUTPUT}`)
}

main().catch(err => {
  console.error(err)
  process.exit(1)
})
