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

async function fetchChunk(startEpoch, durationMinutes) {
  const url = `${BASE}/${PROVIDER_ID}/web?start=${startEpoch}&duration=${durationMinutes}`

  console.log(`[fetch] ${url}`)

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

function makeLogoUrl(logo) {
  if (!logo) return ''
  if (logo.startsWith('http')) return logo
  return `https://www.tvguide.com/a/img/catalog${logo}`
}

async function main() {
  fs.mkdirSync('guides', { recursive: true })

  const dayStart = startOfTodayEpoch()
  const dayEnd = dayStart + DAYS * 24 * 60 * 60
  const totalMinutes = DAYS * 24 * 60

  const channels = new Map()
  const programmes = new Map()

  console.log('[info] starting TVGuide OTA grab')
  console.log(`[info] provider ID: ${PROVIDER_ID}`)
  console.log(`[info] days: ${DAYS}`)
  console.log(`[info] output: ${OUTPUT}`)
  console.log(`[info] chunk minutes: ${CHUNK_MINUTES}`)

  for (let offset = 0; offset < totalMinutes; offset += CHUNK_MINUTES) {
    const chunkStart = dayStart + offset * 60
    const json = await fetchChunk(chunkStart, CHUNK_MINUTES)
    const items = getItems(json)

    if (!items.length) {
      console.log(`[warn] no items found for chunk ${chunkStart}`)
      continue
    }

    for (const item of items) {
      const channel = item.channel
      if (!channel || !channel.sourceId) continue

      const channelId = String(channel.sourceId)

      const fullName =
        channel.fullName ||
        channel.networkName ||
        channel.name ||
        `Channel ${channelId}`

      channels.set(channelId, {
        id: channelId,
        fullName,
        name: channel.name || '',
        number: channel.number || '',
        networkName: channel.networkName || '',
        logo: makeLogoUrl(channel.logo || '')
      })

      const schedules = Array.isArray(item.programSchedules)
        ? item.programSchedules
        : []

      for (const p of schedules) {
        if (!p.startTime || !p.endTime) continue

        if (p.endTime <= dayStart) continue
        if (p.startTime >= dayEnd) continue

        const originalStart = p.startTime
        const originalEnd = p.endTime

        const startTime = Math.max(originalStart, dayStart)
        const endTime = Math.min(originalEnd, dayEnd)

        if (endTime <= startTime) continue

        const key = [
          channelId,
          originalStart,
          originalEnd,
          p.programId || '',
          p.title || ''
        ].join('|')

        programmes.set(key, {
          channelId,
          start: startTime,
          stop: endTime,
          title: p.title || 'Unknown',
          subTitle: p.episodeTitle || p.subtitle || '',
          desc: p.description || p.shortDescription || '',
          category: p.catName || '',
          rating: p.rating || ''
        })
      }
    }
  }

  if (!channels.size) {
    throw new Error('No channels found in TVGuide backend response')
  }

  const sortedChannels = [...channels.values()].sort((a, b) => {
    const an = parseFloat(a.number)
    const bn = parseFloat(b.number)

    if (!Number.isNaN(an) && !Number.isNaN(bn)) return an - bn
    if (!Number.isNaN(an)) return -1
    if (!Number.isNaN(bn)) return 1

    return a.fullName.localeCompare(b.fullName)
  })

  const countsByChannel = new Map()

  for (const p of programmes.values()) {
    countsByChannel.set(p.channelId, (countsByChannel.get(p.channelId) || 0) + 1)
  }

  console.log('')
  console.log('[info] FINAL FULL-DAY PROGRAM TOTALS PER CHANNEL')
  console.log('')

  for (const ch of sortedChannels) {
    console.log(
      `[day-total] ${ch.fullName} | ${ch.number || 'no-number'} | ${ch.id} | ${countsByChannel.get(ch.id) || 0} programme(s)`
    )
  }

  console.log('')
  console.log(`[info] found ${channels.size} channel(s)`)
  console.log(`[info] found ${programmes.size} programme(s) total`)
  console.log('')

  const lines = []

  lines.push('<?xml version="1.0" encoding="UTF-8"?>')
  lines.push('<tv generator-info-name="festy1986 TVGuide OTA">')

  for (const ch of sortedChannels) {
    lines.push(`  <channel id="${xmlEscape(ch.id)}">`)
    lines.push(`    <display-name>${xmlEscape(ch.fullName)}</display-name>`)

    if (ch.name && ch.name !== ch.fullName) {
      lines.push(`    <display-name>${xmlEscape(ch.name)}</display-name>`)
    }

    if (ch.networkName && ch.networkName !== ch.name) {
      lines.push(`    <display-name>${xmlEscape(ch.networkName)}</display-name>`)
    }

    if (ch.number) {
      lines.push(`    <display-name>${xmlEscape(ch.number)}</display-name>`)
    }

    if (ch.logo) {
      lines.push(`    <icon src="${xmlEscape(ch.logo)}" />`)
    }

    lines.push('  </channel>')
  }

  const sortedProgrammes = [...programmes.values()].sort((a, b) => {
    if (a.channelId !== b.channelId) return a.channelId.localeCompare(b.channelId)
    return a.start - b.start
  })

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

  console.log(`[done] wrote ${OUTPUT}`)
}

main().catch(err => {
  console.error(err)
  process.exit(1)
})
