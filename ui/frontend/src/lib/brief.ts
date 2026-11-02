import type { Brief, BriefChunk } from "../api/types";

// A preview of how the server splits the pursuit brief into citable chunks H1, H2...
// Port of rfp_agent.brief.parse_brief; the server's split is the one that counts, this one
// only shows the reviewer what the drafter will cite before they confirm.

const PARAGRAPH_BREAK = /\n[ \t]*\n+/;

// A one-line block that is a markdown heading or ends with a colon: it labels the
// paragraph that follows rather than saying anything citable on its own.
function isHeading(block: string): boolean {
  return !block.includes("\n") && (block.startsWith("#") || block.endsWith(":"));
}

function blocksOf(text: string): string[] {
  return text
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .trim()
    .split(PARAGRAPH_BREAK)
    .map((b) => b.trim())
    .filter(Boolean);
}

export function parseBrief(text: string | null | undefined): Brief | null {
  if (text == null) return null;
  const normalised = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
  if (!normalised) return null;
  const merged: string[] = [];
  let pending: string | null = null;
  for (const block of blocksOf(normalised)) {
    if (isHeading(block)) {
      pending = pending === null ? block : `${pending}\n${block}`;
      continue;
    }
    merged.push(pending === null ? block : `${pending}\n${block}`);
    pending = null;
  }
  if (pending !== null) merged.push(pending);
  const chunks: BriefChunk[] = merged.map((b, i) => ({ id: `H${i + 1}`, text: b }));
  return { text: normalised, chunks };
}

// Section headings for a brief. Template headings left empty are dropped before sending
// (see dropUnfilledTemplate), so an unfilled section neither becomes its own chunk nor
// sticks to the next section's text.
export const BRIEF_SECTIONS = [
  { heading: "Win themes:", hint: "Why we win: the two or three messages every part of the answer should carry." },
  { heading: "Our capabilities and credentials:", hint: "Delivered projects, certifications, partners, people." },
  { heading: "Constraints:", hint: "Team size, locations, budget ceiling, technology we will or will not use." },
  { heading: "Client context:", hint: "What the client said outside the RFP; incumbents; politics." },
  { heading: "Avoid:", hint: "Claims, technologies or wording to stay away from." },
] as const;

export const BRIEF_TEMPLATE = BRIEF_SECTIONS.map((s) => `${s.heading}\n\n`).join("");

const TEMPLATE_HEADINGS: ReadonlySet<string> = new Set(BRIEF_SECTIONS.map((s) => s.heading));

// The text without the template's own headings where nothing was written under them
// (followed by another heading or by the end). Headings the reviewer wrote are kept, as
// the server keeps them; when nothing is dropped the text is returned unchanged.
export function dropUnfilledTemplate(text: string): string {
  const blocks = blocksOf(text);
  const unfilled = (b: string, i: number) =>
    TEMPLATE_HEADINGS.has(b) && (i + 1 === blocks.length || isHeading(blocks[i + 1]));
  if (!blocks.some(unfilled)) return text;
  return blocks.filter((b, i) => !unfilled(b, i)).join("\n\n");
}
