/** Make invisible characters visible in before/after examples: a non-breaking space, a stray line
 * break or a trailing space is exactly the kind of mess the Data Doctor has to show, not hide. */
export function showInvisibles(text: string | null | undefined): string {
  if (text === null || text === undefined) return "∅";
  return text
    .replace(/\u00a0/g, "⍽") // non-breaking space
    .replace(/\r?\n/g, "↵")
    .replace(/\t/g, "⇥")
    .replace(/^ +| +$/g, (spaces) => "␣".repeat(spaces.length)) // leading/trailing spaces
    .replace(/ {2,}/g, (spaces) => "␣".repeat(spaces.length)); // runs of spaces
}
