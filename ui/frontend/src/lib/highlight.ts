// Chunk text and requirement quotes are pymupdf4llm markdown: bold (**), underline (<u>),
// <br> and curly punctuation. We show them as plain text and find the quote inside the
// chunk by comparing a folded form (lower case, straight quotes, collapsed whitespace).

export function plainText(md: string): string {
  return md
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/?[a-z][^>]*>/gi, "")
    .replace(/\*\*|__/g, "")
    .replace(/[ \t]+\n/g, "\n");
}

const FOLD: Record<string, string> = {
  "‘": "'",
  "’": "'",
  "“": '"',
  "”": '"',
  "–": "-",
  "—": "-",
  " ": " ",
};

interface Folded {
  text: string;
  // map[i] is the index in the source string of folded character i
  map: number[];
}

function fold(s: string): Folded {
  let text = "";
  const map: number[] = [];
  for (let i = 0; i < s.length; i++) {
    let c = FOLD[s[i]] ?? s[i];
    if (c === "*") continue; // markdown emphasis, never meaningful in RFP prose
    if (/\s/.test(c)) {
      if (text.endsWith(" ") || text.length === 0) continue;
      c = " ";
    }
    text += c.toLowerCase();
    map.push(i);
  }
  return { text, map };
}

export interface Highlight {
  before: string;
  match: string;
  after: string;
  // true when only the opening of the quote was found (long quotes spanning a table cell)
  partial: boolean;
}

export function highlightQuote(text: string, quote: string): Highlight | null {
  const hay = fold(text);
  const needle = fold(plainText(quote)).text.trim();
  if (!needle) return null;
  let idx = hay.text.indexOf(needle);
  let len = needle.length;
  let partial = false;
  if (idx < 0 && needle.length > 40) {
    const head = needle.slice(0, 40);
    idx = hay.text.indexOf(head);
    len = head.length;
    partial = true;
  }
  if (idx < 0) return null;
  const start = hay.map[idx];
  const end = hay.map[idx + len - 1] + 1;
  return {
    before: text.slice(0, start),
    match: text.slice(start, end),
    after: text.slice(end),
    partial,
  };
}
