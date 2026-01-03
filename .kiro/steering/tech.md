# Tech Stack

## Core Technologies
- **Foundry VTT Module** - JavaScript-based module system
- **Babele** - Translation framework for Foundry VTT compendiums
- **JSON** - Primary data format for translations
- **Python** - Utility scripts for translation workflow

## Key Files
- `module.json` - Module manifest and configuration
- `babele.js` - Babele initialization and converter registration
- `setup.js` - SWADE system settings configuration (Chinese skill names)
- `swade-core.css` - Custom styling for Chinese fonts

## Translation Data Structure
Translation files use Babele's JSON format:
```json
{
  "entries": {
    "English Name": {
      "name": "中文名称",
      "description": "<article>HTML content with translations</article>",
      "category": "类别"
    }
  }
}
```

## Utility Scripts (Python)
Located in `utility/`:
- `extract_text.py` - Extract plain text from JSON for translation
- `html_injector.py` - Inject translations back into HTML structure
- `csv2json.py`, `yml2json.py` - Format converters
- `translate_names.py` - Name translation helpers

## Common Commands
```bash
# Extract text for translation
cd utility
python extract_text.py ../en-US/swade-core-rules.swade-edges.json

# Inject translations back
python html_injector.py ../en-US/source.json translations.csv -o ../zh_Hans/output.json

# Validate JSON syntax
python -m json.tool path/to/file.json
```

## External Services
- **Weblate** - Collaborative translation platform at http://150.109.5.239/engage/swade/
- **GitHub** - Source repository and releases
