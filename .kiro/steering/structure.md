# Project Structure

```
/
├── en-US/                    # English source translations (reference)
│   └── *.json                # Babele format JSON files
├── zh_Hans/                  # Chinese (Simplified) translations
│   └── *.json                # Translated Babele JSON files
├── glossary/                 # Term glossaries
│   ├── swade-glossary.json   # SWADE term mappings (EN→CN)
│   └── swpf-glossary.json    # SWPF term mappings
├── lang/                     # UI language files
│   ├── cn.json               # Chinese UI strings
│   ├── cn.yml                # YAML format (source)
│   └── en.yml                # English reference
├── mappings/                 # Field mapping configurations
│   └── *.json                # Babele field mappings
├── utility/                  # Python translation tools
│   └── *.py                  # Extraction/injection scripts
├── style/                    # Custom fonts
│   ├── cnHeading.TTF         # Chinese heading font
│   └── cnP.ttf               # Chinese paragraph font
├── packs/                    # Foundry compendium packs
├── babele.js                 # Babele module initialization
├── setup.js                  # SWADE system configuration
├── swade-core.css            # Chinese font styling
└── module.json               # Foundry module manifest
```

## File Naming Convention
Translation files follow: `{module}.{compendium}.json`
- Example: `swade-core-rules.swade-edges.json`

## Content Categories
- **swade-core-rules** - Base SWADE content (edges, hindrances, powers, etc.)
- **swpf-core-rules** - Pathfinder for Savage Worlds content
- **swpf-bestiary** - SWPF creature compendium

## Glossary Usage
Use glossary files to maintain consistent terminology across translations. The glossary maps English terms to their official Chinese translations.
