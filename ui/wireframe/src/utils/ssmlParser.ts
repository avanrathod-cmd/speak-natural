/**
 * SSML Parser Utilities
 *
 * Parses SSML markup to extract text and emphasis information
 * for rendering in the UI with stress highlighting.
 */

export interface SSMLPart {
  text: string;
  emphasis: 'none' | 'moderate' | 'strong';
}

export interface ParsedSSML {
  parts: SSMLPart[];
  plainText: string;
}

/**
 * Parse SSML string and extract text with emphasis information.
 *
 * Handles tags like:
 * - <prosody rate="X%">...</prosody> (stripped, content kept)
 * - <emphasis level="moderate|strong">text</emphasis> (parsed for highlighting)
 * - <break time="Xms"/> (converted to space)
 *
 * @param ssml - SSML markup string
 * @returns Parsed parts with emphasis levels and plain text
 */
export const parseSSML = (ssml: string): ParsedSSML => {
  if (!ssml) return { parts: [], plainText: '' };

  // Remove prosody tags but keep content
  let cleaned = ssml
    .replace(/<prosody[^>]*>/gi, '')
    .replace(/<\/prosody>/gi, '')
    .replace(/<break[^>]*\/>/gi, ' ');

  const parts: SSMLPart[] = [];
  const emphasisRegex = /<emphasis\s+level=["']?(moderate|strong)["']?>(.*?)<\/emphasis>/gi;
  let lastIndex = 0;
  let match;

  while ((match = emphasisRegex.exec(cleaned)) !== null) {
    // Add text before the match
    if (match.index > lastIndex) {
      const beforeText = cleaned.slice(lastIndex, match.index);
      if (beforeText.trim()) {
        parts.push({ text: beforeText, emphasis: 'none' });
      }
    }
    // Add the emphasized text
    parts.push({
      text: match[2],
      emphasis: match[1].toLowerCase() as 'moderate' | 'strong'
    });
    lastIndex = emphasisRegex.lastIndex;
  }

  // Add remaining text
  if (lastIndex < cleaned.length) {
    const remainingText = cleaned.slice(lastIndex);
    if (remainingText.trim()) {
      parts.push({ text: remainingText, emphasis: 'none' });
    }
  }

  // If no parts were created (no emphasis tags), treat entire text as one part
  if (parts.length === 0 && cleaned.trim()) {
    parts.push({ text: cleaned.trim(), emphasis: 'none' });
  }

  // Generate plain text
  const plainText = parts.map(p => p.text).join('').replace(/\s+/g, ' ').trim();

  return { parts, plainText };
};
