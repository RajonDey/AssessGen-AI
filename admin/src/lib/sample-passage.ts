/** Synthetic sample passage for local ingest testing — not licensed material. */

const PARAGRAPH =
  "Urban vertical farms use controlled environments to grow leafy greens close to city consumers. " +
  "Engineers monitor humidity, light intensity, and nutrient cycles throughout each growing season. " +
  "Researchers study how reduced transport distance can lower emissions while keeping produce fresh.";

export function buildSamplePassageText(minWords = 780): string {
  const words: string[] = [];
  while (words.length < minWords) {
    words.push(...PARAGRAPH.split(" "));
  }
  const paragraphA = words.slice(0, minWords).join(" ");
  const paragraphB =
    "Policy makers debate how zoning rules should evolve as rooftop agriculture expands across dense districts.";
  return `${paragraphA}\n\n${paragraphB}`;
}
