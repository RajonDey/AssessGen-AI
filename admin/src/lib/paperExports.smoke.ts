/**
 * Smoke checks for paper / TTS export helpers (run with: npx tsx … or node --experimental).
 * Kept as a plain TS module imported by no production path — verify via:
 *   cd admin && npx --yes tsx ../admin/src/lib/paperExports.smoke.ts
 * Or simply typecheck with next build.
 */

import {
  contentAsListeningScriptMarkdown,
  contentAsPaperMarkdown,
  contentAsTtsJson,
  markdownToPrintHtml,
} from "./paperExports";

const listening = {
  title: "Listening Practice",
  speakers: [
    { id: "N1", role: "narrator", gender: "male", accent: "british" },
    { id: "S1", role: "customer", gender: "female", accent: "british" },
  ],
  script: {
    turns: [
      { speaker: "N1", text: "Now look at Part 1." },
      { speaker: "PAUSE", text: "[PAUSE:40]" },
      { speaker: "S1", text: "I'd like to book a room." },
    ],
  },
  parts: [
    {
      partNumber: 1,
      title: "Part 1",
      instructions: "Answer questions 1-2.",
      questionGroups: [
        {
          groupRange: "1-2",
          subInstructions: "Write ONE WORD.",
          questions: [
            {
              questionNumber: "1",
              type: "sentence-completion",
              question: "The guest wants a _______ room.",
            },
            {
              questionNumber: "2",
              type: "sentence-completion",
              question: "Check-in is after _______.",
            },
          ],
        },
      ],
    },
  ],
  answer_key: { "1": "double", "2": "3pm" },
};

const paper = contentAsPaperMarkdown("listening", listening);
if (/I'd like to book/i.test(paper)) {
  throw new Error("Listening paper must not include spoken script dialogue");
}
if (!/Answer key/i.test(paper) || !/double/.test(paper)) {
  throw new Error("Listening paper must include answer key");
}
if (!/guest wants/i.test(paper)) {
  throw new Error("Listening paper must include questions");
}

const tts = contentAsTtsJson(listening);
if (!tts.speakers.length || !tts.script.turns.length) {
  throw new Error("TTS JSON missing speakers/turns");
}
if ("answer_key" in tts || "parts" in tts) {
  throw new Error("TTS JSON must be script-only");
}

const scriptMd = contentAsListeningScriptMarkdown(listening);
if (!/S1:/.test(scriptMd) && !/\*\*S1:\*\*/.test(scriptMd)) {
  throw new Error("Readable script should include speaker lines");
}

const html = markdownToPrintHtml("test", paper);
if (!html.includes("<h1>") || !html.includes("Answer key")) {
  throw new Error("Print HTML incomplete");
}

console.log("paperExports.smoke: ok");
