name: Rename Logos

on:
  workflow_dispatch:

permissions:
  contents: write

jobs:
  rename:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Rename logo files
        run: |
          node <<'EOF'
          const fs = require('fs')
          const path = require('path')

          const dir = './logos'

          if (!fs.existsSync(dir)) {
            console.error('Missing logos folder')
            process.exit(1)
          }

          const map = {
            "grit": "Grit.png",
            "ionplus": "ION Plus.png",
            "ion plus": "ION Plus.png",
            "court tv": "Court TV.png",
            "courttv": "Court TV.png",
            "antenna": "Antenna TV.png",
            "antenna tv": "Antenna TV.png",
            "cozi": "Cozi TV.png",
            "cozi tv": "Cozi TV.png",
            "hallmark drama": "Hallmark Family.png",
            "hallmark family": "Hallmark Family.png",
            "msnbc": "MS NOW HD.png"
          }

          function normalize(name) {
            return name.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
          }

          for (const file of fs.readdirSync(dir)) {
            const ext = path.extname(file).toLowerCase()
            if (!['.png', '.jpg', '.jpeg', '.webp'].includes(ext)) continue

            const base = path.basename(file, ext)
            const norm = normalize(base)

            for (const key in map) {
              if (norm.includes(key)) {
                const newName = map[key]
                const oldPath = path.join(dir, file)
                const newPath = path.join(dir, newName)

                if (oldPath === newPath) {
                  console.log(`Already correct: ${file}`)
                  break
                }

                if (fs.existsSync(newPath)) {
                  console.log(`Target exists, skipping: ${file} -> ${newName}`)
                  break
                }

                fs.renameSync(oldPath, newPath)
                console.log(`Renamed: ${file} -> ${newName}`)
                break
              }
            }
          }
          EOF

      - name: Commit renamed logos
        run: |
          git config user.name "github-actions"
          git config user.email "github-actions@github.com"

          git add logos/

          if git diff --cached --quiet; then
            echo "No logo changes to commit."
          else
            git commit -m "Rename logos to match channels"
            git push
          fi
