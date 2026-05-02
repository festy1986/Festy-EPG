const fs = require('fs')

const PROVIDER_ID = process.env.TVGUIDE_PROVIDER_ID || '9100000664'
const DAYS = Number(process.env.DAYS || 14)

const RAW_OUTPUT = process.env.RAW_OUTPUT || 'guides/OTALocalsguide.raw.xml'
const CURATED_OUTPUT = process.env.CURATED_OUTPUT || 'guides/OTALocalsguide.xml'

const BASE = 'https://backend.tvguide.com/tvschedules/tvguide'

const CURATED_CHANNELS = new Set([
  'ABC PORTLAND',
  'CBS PORTLAND',
  'COMET',
  'COURT TV',
  'CW BOSTON',
  'FOX PORTLAND',
  'GRIT',
  'HEROES & ICONS',
  'ION MYSTERY',
  'LAFF',
  'METV',
  'NBC PORTLAND'
])

function cleanName(channel) {
  const sourceId = String(channel.sourceId || '')
  const full = channel.fullName || ''
  const network = channel.networkName || ''

  const exact = {
    '9233006796': 'NBC PORTLAND',
    '9200009047': 'TRUE CRIME NETWORK',
    '9200013537': 'QUEST',
    '9233012977': '365BLK',
    '9200034015': 'OUTLAW',
    '9233062018': 'SHOP LC',
    '9266078948': 'WEATHER RADAR',
    '9266081191': 'DEFY',

    '9200014312': 'ABC PORTLAND',
    '9200016252': 'METV',
    '9266073627': 'LAFF',
    '9233085019': 'HSN',
    '9200049190': 'GREAT',
    '9233085018': 'METV TOONS',

    '9233005477': 'PBS AUGUSTA',
    '9233015238': 'CREATE AUGUSTA',
    '9233009689': 'WORLD AUGUSTA',
    '9200014885': 'PBS KIDS AUGUSTA',

    '9233001666': 'CBS PORTLAND',
    '9233003676': 'FOX PORTLAND',
    '9200003760': 'THE NEST',

    '9200004423': 'ROAR',
    '9200018453': 'CHARGE',
    '9200005724': 'COMET',
    '9233011099': 'ANTENNA TV',

    '9233009254': 'PBS',
    '9200008827': 'CREATE',
    '9200020318': 'WORLD',
    '9200020602': 'PBS KIDS',

    '9233005684': 'ION PORTLAND',
    '9233005846': 'COURT TV',
    '9233008792': 'BOUNCE TV',
    '9233003377': 'GRIT',
    '9200008618': 'ION PLUS',
    '9233007890': 'BUSTED',
    '9266021286': 'GAME SHOW CENTRAL',
    '9266077100': 'HSN 2',
    '9266077253': 'QVC2',

    '9200006484': 'CW BOSTON',
    '9200020338': 'HEROES & ICONS',
    '9200017556': 'ION MYSTERY',
    '9200066014': 'STORY TELEVISION',
    '9200008505': 'QVC',
    '9266078506': 'NOSEY'
  }

  if (exact[sourceId]) return exact[sourceId]

  if (network) return network.toUpperCase()

  const match = full.match(/\((.*?)\)/)
  if (match) return match[1].toUpperCase()

  return full.toUpperCase()
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
      'user-agent': 'Mozilla/5.0'
    }
  })

  if (!res.ok) {
    throw new Error(`TVGuide request failed: ${res.status} ${res.statusText}`)
  }

  return res.json()
}

function getItems(json) {
  return json?.data?.items || []
}

function buildXml(channels, programmes, generatorName) {
  const lines = []

  lines.push('<?xml version="1.0" encoding="UTF-8"?>')
  lines.push(`<tv generator-info-name="${xmlEscape(generatorName)}">`)

  for (const ch of [...channels.values()].sort((a, b) => a.name.localeCompare(b.name))) {
    lines.push(`  <channel id="${xmlEscape(ch.name)}">`)
    lines.push(`    <display-name>${xmlEscape(ch.name)}</display-name>`)
    if (ch.rawName && ch.rawName !== ch.name) {
      lines.push(`    <display-name>${xmlEscape(ch.rawName)}</display-name>`)
    }
    if (ch.sourceId) {
      lines.push(`    <display-name>${xmlEscape(ch.sourceId)}</display-name>`)
    }
    lines.push('  </channel>')
  }

  for (const p of programmes.sort((a, b) => {
    if (a.start !== b.start) return a.start - b.start
    return a.channelId.localeCompare(b.channelId)
  })) {
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
  return lines.join('\n') + '\n'
}

async function main() {
  fs.mkdirSync('guides', { recursive: true })

  const baseStart = startOfTodayEpoch()

  const rawChannels = new Map()
  const rawProgrammes = []

  const curatedChannels = new Map()
  const curatedProgrammes = []

  console.log('[info] building OTA raw/master and curated guides')
  console.log(`[info] raw output: ${RAW_OUTPUT}`)
  console.log(`[info] curated output: ${CURATED_OUTPUT}`)

  for (let d = 0; d < DAYS; d++) {
    const dayStart = baseStart + d * 86400
    const dayEnd = dayStart + 86400
    const date = new Date(dayStart * 1000).toISOString().slice(0, 10)

    const json = await fetchDay(dayStart)
    const items = getItems(json)

    const rawDay = new Map()
    const curatedDay = new Map()

    for (const item of items) {
      const rawChannel = item.channel
      if (!rawChannel?.sourceId) continue

      const sourceId = String(rawChannel.sourceId)
      const name = cleanName(rawChannel)
      const rawName = rawChannel.fullName || rawChannel.name || name

      rawChannels.set(name, { name, rawName, sourceId })

      if (CURATED_CHANNELS.has(name)) {
        curatedChannels.set(name, { name, rawName, sourceId })
      }

      for (const p of item.programSchedules || []) {
        if (!p.startTime || !p.endTime) continue
        if (p.endTime <= dayStart) continue
        if (p.startTime >= dayEnd) continue

        const start = Math.max(p.startTime, dayStart)
        const stop = Math.min(p.endTime, dayEnd)
        if (stop <= start) continue

        const programme = {
          channelId: name,
          start,
          stop,
          title: p.title || 'Unknown',
          subTitle: p.episodeTitle || p.subtitle || '',
          desc: p.description || p.shortDescription || '',
          category: p.catName || '',
          rating: p.rating || ''
        }

        const key = `${name}|${p.startTime}|${p.endTime}|${p.programId || ''}|${p.title || ''}`

        rawDay.set(key, programme)

        if (CURATED_CHANNELS.has(name)) {
          curatedDay.set(key, programme)
        }
      }
    }

    rawProgrammes.push(...rawDay.values())
    curatedProgrammes.push(...curatedDay.values())

    console.log(`\n=== ${date} ===`)
    console.log(`[raw] ${rawDay.size} programmes`)
    console.log(`[curated] ${curatedDay.size} programmes`)
  }

  fs.writeFileSync(
    RAW_OUTPUT,
    buildXml(rawChannels, rawProgrammes, 'festy1986 OTA Raw Master')
  )

  fs.writeFileSync(
    CURATED_OUTPUT,
    buildXml(curatedChannels, curatedProgrammes, 'festy1986 OTA Locals Curated')
  )

  console.log(`\n[done] wrote raw/master: ${RAW_OUTPUT}`)
  console.log(`[done] raw channels: ${rawChannels.size}`)
  console.log(`[done] raw programmes: ${rawProgrammes.length}`)

  console.log(`\n[done] wrote curated: ${CURATED_OUTPUT}`)
  console.log(`[done] curated channels: ${curatedChannels.size}`)
  console.log(`[done] curated programmes: ${curatedProgrammes.length}`)
}

main().catch(err => {
  console.error(err)
  process.exit(1)
})
