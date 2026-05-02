const fs = require('fs')

const FILE = 'guides/tvguidetivimate.xml'
const BACKUP = 'guides/tvguidetivimate.raw.xml'

const MASTER = [
  // OTA / locals
  'COMET','LAFF','FOX PORTLAND','NBC PORTLAND','ABC PORTLAND','CBS PORTLAND','CW PORTLAND','PBS','METV',
  'ION MYSTERY','COZI TV','COURT TV','GRIT','ANTENNA TV','HEROES & ICONS',

  // core cable
  'NEW ENGLAND CABLE NEWS','NESN','NESN PLUS','NBC SPORTS BOSTON',
  'ESPN','ESPN 2 HD','ESPN NEWS','FOX SPORTS 1','FOX SPORTS 2','NFL NETWORK','NBA TV','MLB NETWORK','NHL NETWORK',
  'CNN','HLN','CNBC','FOX NEWS','MS NOW',
  'USA NETWORK','TNT','TBS','TRU TV','A&E','AMC','FX','FXX','FXM','SYFY',
  'HGTV','FOOD NETWORK','TRAVEL CHANNEL','TLC','DISCOVERY CHANNEL','DISCOVERY LIFE',
  'ANIMAL PLANET','HISTORY CHANNEL','NATIONAL GEOGRAPHIC','NAT GEO WILD',
  'BRAVO','E! ENTERTAINMENT','MTV','VH1','CMT','BET','OWN',
  'DISNEY CHANNEL','CARTOON NETWORK','NICKELODEON',
  'HALLMARK CHANNEL','HALLMARK MYSTERY','HALLMARK DRAMA',
  'GAME SHOW NETWORK','INSP','FETV','UP TV','GREAT AMERICAN FAMILY',

  // HBO (current naming)
  'HBO','HBO 2','HBO Signature','HBO Comedy','HBO Family','HBO Latino',

  // Cinemax (current naming)
  'Cinemax','MoreMax','ActionMax','ThrillerMax','MovieMax','5StarMax','OuterMax',

  // Paramount+/Showtime (current branding)
  'Paramount+ with SHOWTIME','SHOWTIME 2','SHOWTIME EXTREME','SHOWTIME FAMILY ZONE','SHOWTIME NEXT','SHOWTIME WOMEN','SHOWTIME SHOWCASE',

  // STARZ / ENCORE
  'STARZ','STARZ Edge','STARZ Cinema','STARZ Comedy',
  'STARZ ENCORE','STARZ ENCORE ACTION','STARZ ENCORE CLASSIC','STARZ ENCORE SUSPENSE','STARZ ENCORE WESTERNS','STARZ ENCORE FAMILY',

  // MGM+
  'MGM+','MGM+ Hits','MGM+ Marquee','MGM+ Drive-In',

  // Plex channels
  'MoviePlex','RetroPlex','IndiePlex'
]

const OTA = [
  { name:'COMET', tests:[/WPFO.*DT3/i,/COMET/i]},
  { name:'LAFF', tests:[/WMTW.*DT3/i,/LAFF/i]},
  { name:'METV', tests:[/WMTW.*DT2/i]},
  { name:'NBC PORTLAND', tests:[/WCSH/i]},
  { name:'ABC PORTLAND', tests:[/WMTW(?!.*DT2)(?!.*DT3)/i]},
  { name:'CBS PORTLAND', tests:[/WGME(?!.*DT2)/i]},
  { name:'FOX PORTLAND', tests:[/WGME.*DT2/i]},
  { name:'CW PORTLAND', tests:[/WPXT(?!.*DT2)(?!.*DT3)/i]},
  { name:'ION MYSTERY', tests:[/WPXT.*DT3/i]},
  { name:'PBS', tests:[/WCBB/i]}
]

function main() {
  if (!fs.existsSync(FILE)) return console.error('Missing file')

  const xml = fs.readFileSync(FILE,'utf8')
  if (!fs.existsSync(BACKUP)) fs.writeFileSync(BACKUP,xml)

  const raw = [...xml.matchAll(/<channel\b([^>]*)>([\s\S]*?)<\/channel>/g)].map(m=>{
    const attrs = Object.fromEntries([...m[1].matchAll(/(\w+)="([^"]*)"/g)].map(x=>[x[1],x[2]]))
    return {text:m[2].trim(),...attrs}
  })

  const usedIds = new Set()
  const usedNames = new Set()
  const out = []

  function add(ch,name){
    if(!ch || !ch.site_id) return
    if(usedIds.has(ch.site_id) || usedNames.has(name)) return
    usedIds.add(ch.site_id)
    usedNames.add(name)
    out.push({name,site_id:ch.site_id})
    console.log('[ADD]',name,ch.site_id)
  }

  // OTA first (strict call sign match)
  OTA.forEach(o=>{
    const ch = raw.find(r=>{
      const h = r.text + r.xmltv_id
      return o.tests.every(rx=>rx.test(h))
    })
    add(ch,o.name)
  })

  // general matching
  MASTER.forEach(name=>{
    if(usedNames.has(name)) return

    const rx = new RegExp(name.replace(/\s+/g,'.*'),'i')

    const match = raw
      .map(r=>{
        let score=0
        if(rx.test(r.text)||rx.test(r.xmltv_id)) score+=100
        if(/HD/i.test(r.text)) score+=10
        if(/WEST/i.test(r.text)) score-=20
        return {r,score}
      })
      .sort((a,b)=>b.score-a.score)[0]?.r

    add(match,name)
  })

  const outXml = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<channels>',
    ...out.map(c=>`  <channel site="tvguide.com" lang="en" xmltv_id="${c.name.replace(/\s+/g,'.')}.us" site_id="${c.site_id}">${c.name}</channel>`),
    '</channels>'
  ].join('\n')

  fs.writeFileSync(FILE,outXml)
  console.log('DONE:',out.length,'channels')
}

main()
