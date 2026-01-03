// Constants - Field mappings for SWADE items
const SWADE_ITEM_MAPPING = {
  description: "system.description",
  notes: "system.notes",
  actions: "system.actions",
  range: "system.range",
  ammo: "system.ammo",
  category: "system.category",
};

// Extended field mappings for different item types
const SWADE_EDGE_MAPPING = {
  description: "system.description",
  requirements: "system.requirements.value",
  category: "system.category",
};

const SWADE_POWER_MAPPING = {
  description: "system.description",
  range: "system.range",
  rank: "system.rank",
  duration: "system.duration",
  trapping: "system.trapping",
  pp: "system.pp",
};

const SWADE_ACTOR_MAPPING = {
  biography: "system.details.biography.value",
  appearance: "system.details.appearance",
  notes: "system.details.notes.value",
  goals: "system.details.goals.value",
};

// Cache for translated items to enable reuse across compendiums
const translationCache = new Map();

/**
 * Utility function to safely merge objects
 * @param {Object} original - Original object
 * @param {Object} translation - Translation object to merge
 * @returns {Object} Merged object
 */
const safeMerge = (original, translation) => {
  if (!original || !translation) return original || {};
  try {
    return foundry.utils.mergeObject(original, translation, { inplace: false });
  } catch (error) {
    console.warn('SWADE Translation: Failed to merge objects:', error);
    return original;
  }
};

/**
 * Find translation for an item from any translated compendium pack
 * @param {string} itemName - Name of the item to find translation for
 * @param {string} itemType - Type of the item (edge, power, ability, etc.)
 * @param {Object} excludePack - Pack to exclude from search (to avoid self-reference)
 * @returns {Object|null} Translation object or null if not found
 */
const findTranslationFromPacks = (itemName, itemType, excludePack = null) => {
  // Check cache first
  const cacheKey = `${itemType}:${itemName}`;
  if (translationCache.has(cacheKey)) {
    return translationCache.get(cacheKey);
  }

  // Search through all translated Babele packs
  if (!game.babele?.packs) return null;

  for (const pack of game.babele.packs) {
    // Skip excluded pack and untranslated packs
    if (pack === excludePack || !pack.translated) continue;
    
    // Check if this pack has the translation
    if (pack.translations && pack.translations[itemName]) {
      const translation = pack.translations[itemName];
      // Cache the result
      translationCache.set(cacheKey, translation);
      return translation;
    }
  }

  return null;
};

/**
 * Translate embedded items within an actor or other container
 * Implements Requirements 4.1, 4.2 - Reuse translations from compendiums
 * @param {Array} items - Array of embedded items
 * @param {Object} translations - Direct translations for these items (by ID or name)
 * @param {Object} data - Parent document data
 * @param {Object} tc - Translation context (current pack)
 * @returns {Array} Translated items array
 */
const translateEmbeddedItems = (items, translations, data, tc) => {
  if (!Array.isArray(items)) {
    console.warn('SWADE Translation: translateEmbeddedItems received non-array:', items);
    return items || [];
  }

  return items.map((item) => {
    const itemId = item._id || item.id;
    const itemName = item.name;
    const itemType = item.type;

    // Priority 1: Check for direct translation by ID
    if (translations && itemId && translations[itemId]) {
      return safeMerge(item, translations[itemId]);
    }

    // Priority 2: Check for direct translation by name
    if (translations && itemName && translations[itemName]) {
      return safeMerge(item, translations[itemName]);
    }

    // Priority 3: Search in other translated compendiums for reuse
    const packTranslation = findTranslationFromPacks(itemName, itemType, tc);
    if (packTranslation) {
      // Apply the found translation
      const translatedItem = safeMerge(item, packTranslation);
      translatedItem._translationSource = 'compendium-reuse';
      return translatedItem;
    }

    // No translation found, return original
    return item;
  });
};

/**
 * Parse and translate embedded abilities (legacy format support)
 * Handles the [index, abilityData] tuple format used in some SWADE data
 * @param {Array} value - Array of ability tuples
 * @param {Object} translations - Translations object
 * @param {Object} data - Parent document data
 * @param {Object} tc - Translation context
 * @returns {Array} Translated abilities array
 */
const parseEmbeddedAbilities = (value, translations, data, tc) => {
  if (!Array.isArray(value)) return value;
  
  return value.map((item, k) => {
    // Handle tuple format [index, abilityData]
    if (Array.isArray(item) && item.length === 2) {
      const [index, abilityData] = item;
      
      // Try to find translation from other packs
      const pack = game.babele.packs.find(
        (pack) => pack.translated && pack.translations[abilityData.name]
      );
      
      if (pack && pack !== tc) {
        return [
          index,
          safeMerge(
            abilityData,
            pack.translate(abilityData, pack.translations[abilityData.name])
          )
        ];
      }
      return item;
    }
    
    // Handle regular object format
    if (item && typeof item === 'object' && item.name) {
      const pack = game.babele.packs.find(
        (pack) => pack.translated && pack.translations[item.name]
      );
      
      if (pack && pack !== tc) {
        return safeMerge(
          item,
          pack.translate(item, pack.translations[item.name])
        );
      }
    }
    
    return item;
  });
};

/**
 * Recursively translate nested content within an object
 * Implements Requirement 4.4 - Recursive translation of nested fields
 * @param {Object} obj - Object to translate
 * @param {Object} translations - Translations for this object
 * @param {Array} translatableFields - List of field names that should be translated
 * @param {number} depth - Current recursion depth (max 10)
 * @returns {Object} Translated object
 */
const translateNestedContent = (obj, translations, translatableFields = ['name', 'description', 'text', 'notes'], depth = 0) => {
  if (!obj || typeof obj !== 'object' || depth > 10) return obj;
  
  const result = Array.isArray(obj) ? [...obj] : { ...obj };
  
  for (const key of Object.keys(result)) {
    const value = result[key];
    
    // Check if this field has a direct translation
    if (translations && translations[key] !== undefined) {
      if (typeof translations[key] === 'object' && typeof value === 'object') {
        // Recursively translate nested objects
        result[key] = translateNestedContent(value, translations[key], translatableFields, depth + 1);
      } else {
        result[key] = translations[key];
      }
    } else if (typeof value === 'object' && value !== null) {
      // Recursively process nested objects even without direct translation
      result[key] = translateNestedContent(value, null, translatableFields, depth + 1);
    }
  }
  
  return result;
};

/**
 * Load custom CSS styles
 * @param {string} url - URL of the stylesheet to load
 */
const loadStyle = (url) => {
  try {
    const link = document.createElement('link');
    link.type = 'text/css';
    link.rel = 'stylesheet';
    link.href = url;
    document.head.appendChild(link);
  } catch (error) {
    console.error('SWADE Translation: Failed to load style:', error);
  }
};

/**
 * Pages converter for JournalEntry documents
 * Implements Requirement 4.5 - Multi-page journal handling
 * @param {Array} pages - Array of journal pages
 * @param {Object} translations - Translations object (keyed by page ID or name)
 * @returns {Array} Translated pages array
 */
const pagesConverter = (pages, translations) => {
  if (!Array.isArray(pages)) {
    console.warn('SWADE Translation: Pages converter received non-array data:', pages);
    return pages;
  }
  
  return pages.map(page => {
    if (!translations) return page;

    // Try to find translation by ID first, then by name
    const translation = translations[page._id] || translations[page.name];
    if (!translation) return page;

    // Build the translated page object
    const translatedPage = foundry.utils.mergeObject(page, {
      name: translation.name ?? page.name,
      translated: true,
    }, { inplace: false });

    // Handle image caption if present
    if (translation.caption !== undefined || page.image?.caption) {
      translatedPage.image = {
        ...page.image,
        caption: translation.caption ?? page.image?.caption ?? ""
      };
    }

    // Handle source URL if present
    if (translation.src !== undefined) {
      translatedPage.src = translation.src;
    }

    // Handle text content - support both direct text and nested text.content
    if (translation.text !== undefined) {
      if (typeof page.text === 'object') {
        translatedPage.text = {
          ...page.text,
          content: translation.text
        };
      } else {
        translatedPage.text = translation.text;
      }
    }

    return translatedPage;
  });
};

/**
 * SWADE Item converter with full field mapping support
 * @param {Array} items - Array of items to translate
 * @param {Object} translations - Translations object
 * @returns {Array} Translated items array
 */
const swadeItemConverter = (items, translations) => {
  try {
    if (!items) {
      console.warn('SWADE Translation: SWADE item converter received null/undefined items');
      return [];
    }

    const itemsArray = Array.isArray(items) ? items : [items];
    
    // Get the converter function from Babele
    const converter = game.babele?.converters?.fromPack?.(SWADE_ITEM_MAPPING, "Item");
    if (typeof converter !== 'function') {
      // Fallback to manual translation if Babele converter not available
      return translateEmbeddedItems(itemsArray, translations, null, null);
    }

    // Apply the Babele converter
    return converter(itemsArray, translations);
  } catch (error) {
    console.error('SWADE Translation: Error in SWADE item converter:', error);
    return Array.isArray(items) ? items : [items];
  }
};

/**
 * Actions converter for translating action names and descriptions
 * @param {Object} actions - Actions object with skill and additional actions
 * @param {Object} translations - Translations for actions
 * @returns {Object} Translated actions object
 */
const actionsConverter = (actions, translations) => {
  if (!actions || typeof actions !== 'object') return actions;
  if (!translations) return actions;

  const result = { ...actions };

  // Translate skill name
  if (translations.skill) {
    result.skill = translations.skill;
  }

  // Translate additional actions
  if (actions.additional && translations.additional) {
    result.additional = {};
    for (const [key, action] of Object.entries(actions.additional)) {
      const actionTranslation = translations.additional[key];
      if (actionTranslation) {
        result.additional[key] = safeMerge(action, actionTranslation);
      } else {
        result.additional[key] = action;
      }
    }
  }

  return result;
};

// Initialize Babele
Hooks.once("babele.init", (babele) => {
  if (typeof Babele === "undefined") {
    console.error("SWADE Translation: Babele module not found");
    return;
  }

  try {
    // Register module with Babele
    babele.register({
      module: "swade_compendium_chn",
      lang: "cn",
      dir: "compendium",
    });

    // Load custom styles for Chinese fonts
    loadStyle('../../modules/swade_compendium_chn/swade-core.css');

    // Verify converters are available
    if (!babele.converters) {
      console.error("SWADE Translation: Babele Converters not initialized");
      return;
    }

    // Register all converters
    babele.registerConverters({
      // Legacy embedded abilities converter
      translateEmbeddedAbilities: parseEmbeddedAbilities,
      
      // Journal pages converter (Requirement 4.5)
      pages: pagesConverter,
      
      // Main SWADE item converter with field mapping
      SWADE_ITEM_CONVERTERS: swadeItemConverter,
      
      // Embedded items converter with compendium reuse (Requirements 4.1, 4.2)
      embeddedItems: translateEmbeddedItems,
      
      // Nested content translator (Requirement 4.4)
      nestedContent: translateNestedContent,
      
      // Actions converter for skill and additional actions
      actions: actionsConverter,
    });

    console.log("SWADE Translation: Babele converters registered successfully");

  } catch (error) {
    console.error('SWADE Translation: Failed to initialize Babele:', error);
  }
});

// Clear translation cache when world is closed or packs are updated
Hooks.on("closeWorld", () => {
  translationCache.clear();
});

// Export functions for testing (if in Node.js environment)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    translateEmbeddedItems,
    parseEmbeddedAbilities,
    translateNestedContent,
    pagesConverter,
    actionsConverter,
    findTranslationFromPacks,
    safeMerge,
    SWADE_ITEM_MAPPING,
    SWADE_EDGE_MAPPING,
    SWADE_POWER_MAPPING,
    SWADE_ACTOR_MAPPING,
  };
}
