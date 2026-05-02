const fs = require('fs');
const path = require('path');

const dir = './logos'; // change if needed

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
};

function normalize(name) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

fs.readdirSync(dir).forEach(file => {
  const ext = path.extname(file);
  const base = path.basename(file, ext);
  const norm = normalize(base);

  for (const key in map) {
    if (norm.includes(key)) {
      const newName = map[key];
      const oldPath = path.join(dir, file);
      const newPath = path.join(dir, newName);

      try {
        fs.renameSync(oldPath, newPath);
        console.log(`Renamed: ${file} → ${newName}`);
      } catch (e) {}
      break;
    }
  }
});
