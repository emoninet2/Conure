// artworkHelper.js
import { loadArtwork, saveArtwork } from './api'; // adjust the path as needed

// Extract data from context into an object for saving
export const serializeArtworkContext = (context) => {
  const allData = {};
  for (const sectionKey in context) {
    const section = context[sectionKey];
    for (const stateKey in section) {
      if (stateKey.startsWith('set')) continue;
      allData[stateKey] = section[stateKey];
    }
  }
  return allData;
};

// Saves the artwork data using the provided API function
export const saveArtworkData = async (context) => {
  const allData = serializeArtworkContext(context);
  try {
    await saveArtwork(allData);
    return { success: true, message: '✅ Artwork saved!' };
  } catch (error) {
    return { success: false, message: '❌ Save failed: ' + error.message };
  }
};

// Loads artwork data and applies the values to the context
export const loadAndApplyArtwork = async (context) => {
  try {
    const result = await loadArtwork();
    const data = result.data || {};
    // Define the mapping between data keys and context keys
    const orderedKeys = [
      ['metaData', 'metadata'],
      ['parameterData', 'parameter'],
      ['layerData', 'layers'],
      ['viaData', 'vias'],
      ['viaPadStackData', 'viaPadStack'],
      ['bridgeData', 'bridges'],
      ['portData', 'ports'],
      ['simPortData', 'ports'],
      ['armData', 'arms'],
      ['segmentData', 'segments'],
      ['guardRingData', 'guardRing'],
      ['guardRingDummyData', 'guardRing'],
      ['useGuardRing', 'guardRing'],
      ['guardRingDistance', 'guardRing']
    ];

    for (const [dataKey, contextKey] of orderedKeys) {
      const section = context[contextKey];
      if (!section) continue;
      for (const stateKey in section) {
        if (
          typeof section[stateKey] === 'function' &&
          stateKey.startsWith('set')
        ) {
          const expectedKey =
            stateKey.replace(/^set/, '').charAt(0).toLowerCase() +
            stateKey.replace(/^set/, '').slice(1);
          if ((expectedKey === dataKey || dataKey === expectedKey) && data[dataKey] !== undefined) {
            section[stateKey](data[dataKey]);
          }
        }
      }
    }
    return { success: true, message: '✅ Artwork loaded!' };
  } catch (error) {
    return { success: false, message: '❌ Load failed: ' + error.message };
  }
};
