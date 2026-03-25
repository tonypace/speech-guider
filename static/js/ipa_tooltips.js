// IPA Phoneme-to-Example Word Mapping
// Comprehensive phoneme inventory with tooltip examples

const IPATooltips = {
  // === PLOSIVES ===
  'p': { word: 'pat', highlight: 'p' },
  'b': { word: 'bat', highlight: 'b' },
  't': { word: 'top', highlight: 't' },
  'd': { word: 'dad', highlight: 'd' },
  'k': { word: 'cat', highlight: 'c' },
  'g': { word: 'go', highlight: 'g' },
  'q': { word: 'qat', highlight: 'q', lang: 'Arabic' },
  'ʔ': { word: 'uh-oh', highlight: '-', lang: 'glottal stop' },

  // === ASPIRATED PLOSIVES ===
  'pʰ': { word: 'pit', highlight: 'p', lang: 'aspirated' },
  'tʰ': { word: 'top', highlight: 't', lang: 'aspirated' },
  'kʰ': { word: 'cat', highlight: 'c', lang: 'aspirated' },

  // === RETROFLEX PLOSIVES ===
  'ʈ': { word: 'ṭa', highlight: 'ṭ', lang: 'Hindi' },
  'ɖ': { word: 'ḍa', highlight: 'ḍ', lang: 'Hindi' },

  // === FRICATIVES ===
  'f': { word: 'fin', highlight: 'f' },
  'v': { word: 'van', highlight: 'v' },
  'θ': { word: 'thin', highlight: 'th' },
  'ð': { word: 'that', highlight: 'th' },
  's': { word: 'see', highlight: 's' },
  'z': { word: 'zoo', highlight: 'z' },
  'ʃ': { word: 'ship', highlight: 'sh' },
  'ʒ': { word: 'treasure', highlight: 's' },
  'h': { word: 'hat', highlight: 'h' },
  'x': { word: 'Bach', highlight: 'ch', lang: 'German' },
  'χ': { word: 'Baḥrain', highlight: 'ḥ', lang: 'Arabic' },
  'ħ': { word: 'Muḥammad', highlight: 'ḥ', lang: 'Arabic' },

  // Retroflex fricatives
  'ʂ': { word: 'ṣa', highlight: 'ṣ', lang: 'Hindi' },
  'ʐ': { word: 'zha', highlight: 'zh', lang: 'Mandarin' },

  // Pharyngeal fricatives
  'ʕ': { word: 'ayn', highlight: 'ay', lang: 'Arabic' },

  // === AFFRICATES ===
  'tʃ': { word: 'church', highlight: 'ch' },
  'dʒ': { word: 'judge', highlight: 'j' },
  'ts': { word: 'tsunami', highlight: 'ts' },

  // === NASALS ===
  'm': { word: 'mom', highlight: 'm' },
  'n': { word: 'no', highlight: 'n' },
  'ŋ': { word: 'sing', highlight: 'ng' },
  'ɲ': { word: 'senor', highlight: 'n', lang: 'Spanish' },

  // === APPROXIMANTS ===
  'l': { word: 'let', highlight: 'l' },
  'r': { word: 'red', highlight: 'r' },
  'w': { word: 'wet', highlight: 'w' },
  'j': { word: 'yes', highlight: 'y' },
  'ɹ': { word: 'red', highlight: 'r' },
  'ɻ': { word: 'retroflex r', highlight: 'r', lang: 'some languages' },

  // === VOWELS - Short ===
  'ɪ': { word: 'kit', highlight: 'i' },
  'ɛ': { word: 'dress', highlight: 'e' },
  'æ': { word: 'trap', highlight: 'a' },
  'ʌ': { word: 'strut', highlight: 'u' },
  'ʊ': { word: 'foot', highlight: 'oo' },
  'ə': { word: 'about', highlight: 'a' },
  'ɜ': { word: 'nurse', highlight: 'ur' },
  'ɨ': { word: 'roses', highlight: 'e' },
  'ɒ': { word: 'lot', highlight: 'o' },

  // === VOWELS - Long ===
  'i': { word: 'fleece', highlight: 'ee' },
  'iː': { word: 'fleece', highlight: 'ee' },
  'e': { word: 'face', highlight: 'a' },
  'eː': { word: 'face', highlight: 'a' },
  'ɑ': { word: 'father', highlight: 'a' },
  'ɑː': { word: 'father', highlight: 'a' },
  'ɔ': { word: 'thought', highlight: 'ough' },
  'ɔː': { word: 'thought', highlight: 'ough' },
  'u': { word: 'goose', highlight: 'oo' },
  'uː': { word: 'goose', highlight: 'oo' },
  'o': { word: 'goat', highlight: 'o' },
  'oː': { word: 'goat', highlight: 'o' },
  'ɝ': { word: 'nurse', highlight: 'ur' },
  'ɚ': { word: 'butter', highlight: 'er' },
  'æː': { word: 'trap long', highlight: 'a' },

  // === DIPHTHONGS ===
  'aɪ': { word: 'price', highlight: 'i' },
  'eɪ': { word: 'face', highlight: 'a' },
  'ɔɪ': { word: 'choice', highlight: 'oi' },
  'aʊ': { word: 'mouth', highlight: 'ou' },
  'oʊ': { word: 'goat', highlight: 'o' },
  'iə': { word: 'near', highlight: 'ea' },
  'ʊə': { word: 'cure', highlight: 'u' },
};

function wrapIPATooltip(phoneme) {
  const data = IPATooltips[phoneme];
  
  // Always return with tooltip wrapper, even if no example word exists
  if (!data) {
    return `<span class="ipa-phoneme" data-phoneme="${phoneme}" data-tooltip="/${phoneme}/">/${phoneme}/</span>`;
  }

  const word = data.word;
  const highlight = data.highlight;
  const lang = data.lang ? ` (${data.lang})` : '';
  
  // Build tooltip text with bold highlight
  let tooltipText;
  const highlightIndex = word.toLowerCase().indexOf(highlight.toLowerCase());
  if (highlightIndex >= 0) {
    const before = word.slice(0, highlightIndex);
    const match = word.slice(highlightIndex, highlightIndex + highlight.length);
    const after = word.slice(highlightIndex + highlight.length);
    tooltipText = `/${phoneme}/ as in ${before}**${match.toUpperCase()}**${after}${lang}`;
  } else {
    tooltipText = `/${phoneme}/ as in ${word}${lang}`;
  }

  return `<span class="ipa-phoneme" data-phoneme="${phoneme}" data-tooltip="${tooltipText}">/${phoneme}/</span>`;
}

window.IPATooltips = IPATooltips;
window.wrapIPATooltip = wrapIPATooltip;

// Use event delegation for dynamically added elements
document.addEventListener('mouseover', function(e) {
    // Find the closest ipa-phoneme element
    const phonemeEl = e.target.closest('.ipa-phoneme');
    if (phonemeEl) {
        const tooltipText = phonemeEl.getAttribute('data-tooltip');
        if (!tooltipText) return;

        let tooltip = phonemeEl.querySelector('.ipa-tooltip');
        if (!tooltip) {
            tooltip = document.createElement('span');
            tooltip.className = 'ipa-tooltip';
            phonemeEl.appendChild(tooltip);
        }

        const htmlContent = tooltipText.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        tooltip.innerHTML = htmlContent;
        tooltip.classList.add('visible');
    }
});

document.addEventListener('mouseout', function(e) {
    const phonemeEl = e.target.closest('.ipa-phoneme');
    if (phonemeEl) {
        const tooltip = phonemeEl.querySelector('.ipa-tooltip');
        if (tooltip) {
            tooltip.classList.remove('visible');
        }
    }
});
