/**
 * Paper / script export helpers for Generate downloads.
 *
 * Paper (all modules): questions + answer key in one Markdown document.
 * Listening only: separate TTS JSON (speakers + turns) and optional readable script.
 * Visual/image briefs are excluded from paper/PDF by default; use vendor pack for those.
 */

export type PaperContent = Record<string, unknown>;

export type PaperExportOptions = {
  /** Include illustrator visual_brief / visual / images blocks. Default false for candidate paper. */
  includeVisualBriefs?: boolean;
};

const DEFAULT_PAPER_OPTS: Required<PaperExportOptions> = {
  includeVisualBriefs: false,
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function stripHtml(text: string): string {
  return text.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
}

function escapeMd(text: string): string {
  return text.replace(/\r\n/g, "\n");
}

function formatAnswerKey(answerKey: unknown): string {
  const lines: string[] = ["## Answer key", ""];
  const rec = asRecord(answerKey);
  if (rec) {
    const keys = Object.keys(rec).sort((a, b) => {
      const na = Number(a);
      const nb = Number(b);
      if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
      return a.localeCompare(b);
    });
    for (const k of keys) {
      const v = rec[k];
      const text =
        typeof v === "string" || typeof v === "number"
          ? String(v)
          : JSON.stringify(v);
      lines.push(`- **${k}.** ${text}`);
    }
    lines.push("");
    return lines.join("\n");
  }
  if (Array.isArray(answerKey)) {
    answerKey.forEach((v, i) => {
      lines.push(`- **${i + 1}.** ${typeof v === "string" ? v : JSON.stringify(v)}`);
    });
    lines.push("");
    return lines.join("\n");
  }
  return "";
}

function appendVisualBlocks(
  lines: string[],
  q: Record<string, unknown>,
  includeVisualBriefs: boolean,
): void {
  if (!includeVisualBriefs) return;

  const brief = q.visual_brief ?? q.visualBrief ?? q.visual;
  if (brief && typeof brief === "object") {
    lines.push("");
    lines.push("*Visual brief (for illustrator):*");
    lines.push("```json");
    lines.push(JSON.stringify(brief, null, 2));
    lines.push("```");
  }
  const images = asArray(q.images);
  if (images.length) {
    lines.push("");
    lines.push("*Images:*");
    lines.push("```json");
    lines.push(JSON.stringify(images, null, 2));
    lines.push("```");
  }
}

function formatOptions(
  options: unknown,
  lines: string[],
): void {
  if (Array.isArray(options) && options.length) {
    options.forEach((opt, i) => {
      const letter = String.fromCharCode(65 + i);
      if (typeof opt === "string") {
        lines.push(`- ${letter}. ${stripHtml(opt)}`);
      } else {
        const o = asRecord(opt);
        const label = o?.label ?? o?.text ?? o?.value ?? JSON.stringify(opt);
        lines.push(`- ${letter}. ${stripHtml(String(label))}`);
      }
    });
    return;
  }
  const rec = asRecord(options);
  if (!rec) return;
  const keys = Object.keys(rec).sort((a, b) => {
    if (a.length === 1 && b.length === 1) return a.localeCompare(b);
    const na = Number(a);
    const nb = Number(b);
    if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
    return a.localeCompare(b);
  });
  for (const k of keys) {
    const v = rec[k];
    const text = typeof v === "string" ? v : JSON.stringify(v);
    const letter = /^[A-Za-z]$/.test(k) ? k.toUpperCase() : k;
    lines.push(`- ${letter}. ${stripHtml(text)}`);
  }
}

function formatNotesOutline(
  outline: unknown,
  lines: string[],
): void {
  const asSections = (node: unknown): unknown[] => {
    if (Array.isArray(node)) return node;
    const rec = asRecord(node);
    if (!rec) return [];
    if (Array.isArray(rec.sections)) return rec.sections;
    if (Array.isArray(rec.items)) return rec.items;
    return [];
  };

  const titleRec = asRecord(outline);
  if (titleRec && typeof titleRec.title === "string" && titleRec.title.trim()) {
    lines.push(`**${titleRec.title.trim()}**`);
    lines.push("");
  }

  for (const sec of asSections(outline)) {
    const s = asRecord(sec);
    if (!s) {
      if (typeof sec === "string" && sec.trim()) lines.push(`- ${sec.trim()}`);
      continue;
    }
    const heading =
      (typeof s.heading === "string" && s.heading) ||
      (typeof s.title === "string" && s.title) ||
      "";
    if (heading) {
      lines.push(`#### ${heading}`);
      lines.push("");
    }
    const items = asArray(s.items ?? s.lines ?? s.rows);
    for (const item of items) {
      if (typeof item === "string") {
        lines.push(`- ${item}`);
        continue;
      }
      const it = asRecord(item);
      if (!it) continue;
      const text =
        (typeof it.content === "string" && it.content) ||
        (typeof it.text === "string" && it.text) ||
        "";
      if (text) lines.push(`- ${stripHtml(text)}`);
    }
    lines.push("");
  }
}

function formatQuestion(
  q: Record<string, unknown>,
  fallbackNum: number,
  opts: Required<PaperExportOptions>,
  groupCtx?: { skipStem?: boolean },
): string[] {
  const lines: string[] = [];
  const num =
    q.questionNumber ?? q.number ?? q.label ?? q.id ?? fallbackNum;
  const stem =
    (typeof q.question === "string" && q.question) ||
    (typeof q.title === "string" && q.title) ||
    (typeof q.prompt === "string" && q.prompt) ||
    (typeof q.text === "string" && q.text) ||
    (typeof q.notes === "string" && q.notes) ||
    "";
  const type = typeof q.type === "string" ? q.type : "";
  if (groupCtx?.skipStem) {
    // Shared summary/notes already printed; only show number marker if needed
    return lines;
  }
  lines.push(`**${num}${type ? ` (${type})` : ""}**`);
  if (stem) lines.push(stripHtml(stem));

  formatOptions(q.options, lines);

  // Form / notes style nested sections
  const sections = asArray(q.sections);
  for (const sec of sections) {
    const s = asRecord(sec);
    if (!s) continue;
    const rows = asArray(s.rows);
    for (const row of rows) {
      const r = asRecord(row);
      if (!r) continue;
      const label = typeof r.rowLabel === "string" ? r.rowLabel : "";
      const cells = asArray(r.cells)
        .map((c) => {
          if (typeof c === "string") return c;
          const cell = asRecord(c);
          if (!cell) return "";
          if (cell.isAnswer) return `______(${cell.questionNumber ?? "?"})`;
          return typeof cell.text === "string" ? cell.text : "";
        })
        .filter(Boolean)
        .join(" ");
      lines.push(`- ${label} ${cells}`.trim());
    }
  }

  appendVisualBlocks(lines, q, opts.includeVisualBriefs);

  lines.push("");
  return lines;
}

function formatQuestionGroup(
  group: Record<string, unknown>,
  opts: Required<PaperExportOptions>,
): string[] {
  const lines: string[] = [];
  const instruction =
    (typeof group.instruction === "string" && group.instruction) ||
    (typeof group.subInstructions === "string" && group.subInstructions) ||
    (typeof group.instructions === "string" && group.instructions) ||
    "";
  const range =
    (typeof group.groupRange === "string" && group.groupRange) ||
    (typeof group.title === "string" && group.title) ||
    "";
  if (range || instruction) {
    lines.push(`### ${range || "Questions"}`);
    if (instruction) lines.push(stripHtml(instruction));
    lines.push("");
  }
  if (opts.includeVisualBriefs) {
    appendVisualBlocks(lines, group, true);
  }

  const outline =
    group.notesOutline ?? group.notes_outline ?? group.outline ?? group.sections;
  const sharedSummary =
    (typeof group.summary === "string" && group.summary) ||
    (typeof group.notes === "string" && group.notes) ||
    (typeof group.summaryText === "string" && group.summaryText) ||
    "";
  const groupType = typeof group.type === "string" ? group.type.toLowerCase() : "";
  const isSummaryGroup =
    groupType.includes("summary") ||
    Boolean(sharedSummary && sharedSummary.split(/\s+/).length >= 40);
  const isNotesOutline =
    Boolean(outline) &&
    (groupType.includes("note") ||
      group.notesOutline != null ||
      group.notes_outline != null ||
      group.outline != null);

  if (isNotesOutline && outline) {
    formatNotesOutline(outline, lines);
  } else if (isSummaryGroup && sharedSummary) {
    lines.push(stripHtml(sharedSummary));
    lines.push("");
  }

  formatOptions(group.options ?? group.headings ?? group.bank, lines);
  if (group.options || group.headings || group.bank) lines.push("");

  const questions = asArray(group.questions);
  const skipPerQuestionStem = Boolean(
    (isSummaryGroup && sharedSummary) || (isNotesOutline && outline),
  );
  questions.forEach((q, i) => {
    const rec = asRecord(q);
    if (rec) {
      lines.push(
        ...formatQuestion(rec, i + 1, opts, {
          skipStem: skipPerQuestionStem,
        }),
      );
    }
  });
  return lines;
}

function formatListeningPaperBody(
  content: PaperContent,
  opts: Required<PaperExportOptions>,
): string {
  const lines: string[] = [];
  const title =
    (typeof content.title === "string" && content.title) ||
    "Listening Practice Paper";
  lines.push(`# ${title}`);
  lines.push("");
  lines.push(
    "_Candidate paper — questions and answer key. Script / audio is provided separately._",
  );
  lines.push("");

  const parts = asArray(content.parts);
  if (parts.length) {
    parts.forEach((part, idx) => {
      const p = asRecord(part);
      if (!p) return;
      const n = p.partNumber ?? idx + 1;
      const partTitle =
        (typeof p.title === "string" && p.title) || `Part ${n}`;
      lines.push(`## ${partTitle}`);
      if (typeof p.instructions === "string" && p.instructions) {
        lines.push(stripHtml(p.instructions));
        lines.push("");
      }
      for (const g of asArray(p.questionGroups)) {
        const group = asRecord(g);
        if (group) lines.push(...formatQuestionGroup(group, opts));
      }
    });
  } else {
    for (const g of asArray(content.questionGroups)) {
      const group = asRecord(g);
      if (group) lines.push(...formatQuestionGroup(group, opts));
    }
  }

  const keyMd = formatAnswerKey(content.answer_key ?? content.answerKey);
  if (keyMd) lines.push(keyMd);
  return escapeMd(lines.join("\n").trim() + "\n");
}

function formatReadingPaperBody(
  content: PaperContent,
  opts: Required<PaperExportOptions>,
): string {
  const lines: string[] = [];
  const title =
    (typeof content.title === "string" && content.title) ||
    "Reading Practice Paper";
  lines.push(`# ${title}`);
  lines.push("");

  const sections = asArray(content.sections);
  if (sections.length) {
    sections.forEach((sec, idx) => {
      const s = asRecord(sec);
      if (!s) return;
      const secTitle =
        (typeof s.title === "string" && s.title) || `Passage ${idx + 1}`;
      lines.push(`## ${secTitle}`);
      lines.push("");
      const passage = s.passage;
      if (typeof passage === "string" && passage.trim()) {
        lines.push(passage.trim());
        lines.push("");
      } else if (Array.isArray(passage)) {
        lines.push(passage.map(String).join("\n\n"));
        lines.push("");
      } else if (typeof s.text === "string") {
        lines.push(s.text.trim());
        lines.push("");
      }
      for (const g of asArray(s.questionGroups)) {
        const group = asRecord(g);
        if (group) lines.push(...formatQuestionGroup(group, opts));
      }
      const qs = asArray(s.questions);
      if (qs.length && !asArray(s.questionGroups).length) {
        qs.forEach((q, i) => {
          const rec = asRecord(q);
          if (rec) lines.push(...formatQuestion(rec, i + 1, opts));
        });
      }
    });
  }

  const keyMd = formatAnswerKey(content.answer_key ?? content.answerKey);
  if (keyMd) lines.push(keyMd);
  return escapeMd(lines.join("\n").trim() + "\n");
}

function formatWritingPaperBody(
  content: PaperContent,
  opts: Required<PaperExportOptions>,
): string {
  const lines: string[] = [];
  const title =
    (typeof content.title === "string" && content.title) ||
    "Writing Practice Paper";
  lines.push(`# ${title}`);
  lines.push("");

  const sections = asArray(content.sections);
  if (sections.length) {
    sections.forEach((sec, idx) => {
      const s = asRecord(sec);
      if (!s) return;
      const secTitle =
        (typeof s.title === "string" && s.title) || `Task ${idx + 1}`;
      lines.push(`## ${secTitle}`);
      if (typeof s.instructions === "string") {
        lines.push(s.instructions);
        lines.push("");
      }
      for (const q of asArray(s.questions)) {
        const rec = asRecord(q);
        if (rec) lines.push(...formatQuestion(rec, idx + 1, opts));
      }
    });
  } else if (typeof content.prompt === "string") {
    lines.push(content.prompt);
    lines.push("");
  }

  const keyMd = formatAnswerKey(content.answer_key ?? content.answerKey);
  if (keyMd) lines.push(keyMd);
  return escapeMd(lines.join("\n").trim() + "\n");
}

/** Remove illustrator / visual-brief blocks from freeform document markdown. */
export function stripVisualBriefsFromDocument(doc: string): string {
  let text = doc;
  // Fenced blocks after a visual-brief heading
  text = text.replace(
    /^#{1,3}\s*(visual\s*brief|vendor\s*brief|image\s*brief|illustrator)[^\n]*\n+```[\s\S]*?```/gim,
    "",
  );
  // Italic/bold callouts
  text = text.replace(
    /^\*+Visual brief[^*]*\*+[^\n]*\n+```[\s\S]*?```/gim,
    "",
  );
  text = text.replace(
    /^#{1,3}\s*(visual\s*brief|vendor\s*brief|image\s*brief|illustrator)[^\n]*\n(?:.*\n)*?(?=^#{1,3}\s|$)/gim,
    "",
  );
  // Standalone JSON fences that look like visual briefs
  text = text.replace(
    /```json\s*\n\s*\{[\s\S]*?"(?:type|scenario|layout|kind|data_story|must_show)"[\s\S]*?\n```/gi,
    "",
  );
  text = text.replace(/\n{3,}/g, "\n\n");
  return text.trim();
}

function stripListeningScriptFromDocument(doc: string): string {
  let text = doc.replace(/```json[\s\S]*?```/gi, "");
  text = text.replace(/^##?\s*Script[\s\S]*?(?=^##?\s|$)/gim, "");
  text = text.replace(/^##?\s*Transcript[\s\S]*?(?=^##?\s|$)/gim, "");
  return stripVisualBriefsFromDocument(text);
}

/**
 * Build a candidate/teacher paper Markdown: questions + answers together.
 * Listening papers omit the spoken script (script is a separate download).
 * Visual briefs excluded unless includeVisualBriefs is true.
 */
export function contentAsPaperMarkdown(
  module: string,
  content: PaperContent,
  options?: PaperExportOptions,
): string {
  const opts: Required<PaperExportOptions> = {
    ...DEFAULT_PAPER_OPTS,
    ...options,
  };
  const doc = content.document;
  const hasStructure =
    asArray(content.parts).length > 0 ||
    asArray(content.sections).length > 0 ||
    asArray(content.questionGroups).length > 0;

  if (module === "listening") {
    if (hasStructure) return formatListeningPaperBody(content, opts);
    if (typeof doc === "string" && doc.trim()) {
      let body = stripListeningScriptFromDocument(doc);
      if (!opts.includeVisualBriefs) body = stripVisualBriefsFromDocument(body);
      return (
        body +
        "\n\n" +
        (formatAnswerKey(content.answer_key) || "")
      ).trim() + "\n";
    }
    return formatListeningPaperBody(content, opts);
  }

  if (module === "writing") {
    if (hasStructure) return formatWritingPaperBody(content, opts);
    if (typeof doc === "string" && doc.trim()) {
      const body = opts.includeVisualBriefs
        ? doc.trim()
        : stripVisualBriefsFromDocument(doc);
      return escapeMd(body + "\n");
    }
    return formatWritingPaperBody(content, opts);
  }

  if (hasStructure) return formatReadingPaperBody(content, opts);
  if (typeof doc === "string" && doc.trim()) {
    let body = opts.includeVisualBriefs
      ? doc.trim()
      : stripVisualBriefsFromDocument(doc);
    body = escapeMd(body + "\n");
    const keyMd = formatAnswerKey(content.answer_key ?? content.answerKey);
    if (keyMd && !/answer key/i.test(body)) return body + "\n" + keyMd;
    return body;
  }
  return formatReadingPaperBody(content, opts);
}

/** Vendor / illustrator pack: visual briefs only (no full candidate paper required). */
export function contentAsVendorPackMarkdown(
  module: string,
  content: PaperContent,
): string {
  const full = contentAsPaperMarkdown(module, content, {
    includeVisualBriefs: true,
  });
  const lines: string[] = [
    `# ${module} — Vendor / image pack`,
    "",
    "_Illustrator briefs and image placeholders. Not a candidate paper._",
    "",
  ];

  // Extract visual brief sections from the full with-briefs export
  const briefBlocks: string[] = [];
  const re =
    /\*Visual brief[^*]*\*:\s*\n```json\n([\s\S]*?)```/gi;
  let m: RegExpExecArray | null;
  let i = 1;
  while ((m = re.exec(full)) !== null) {
    briefBlocks.push(`## Brief ${i++}\n\n\`\`\`json\n${m[1].trim()}\n\`\`\`\n`);
  }

  // Also walk structure for any briefs not caught above
  const walk = (node: unknown, path: string) => {
    const rec = asRecord(node);
    if (!rec) return;
    const brief = rec.visual_brief ?? rec.visualBrief ?? rec.visual;
    if (brief && typeof brief === "object") {
      briefBlocks.push(
        `## ${path}\n\n\`\`\`json\n${JSON.stringify(brief, null, 2)}\n\`\`\`\n`,
      );
    }
    for (const g of asArray(rec.questionGroups)) walk(g, path);
    for (const q of asArray(rec.questions)) {
      const qr = asRecord(q);
      const label = qr
        ? String(qr.questionNumber ?? qr.number ?? qr.id ?? "item")
        : "item";
      walk(q, `${path} / Q${label}`);
    }
    for (const p of asArray(rec.parts)) {
      const pr = asRecord(p);
      walk(p, `Part ${pr?.partNumber ?? "?"}`);
    }
    for (const s of asArray(rec.sections)) {
      const sr = asRecord(s);
      walk(s, String(sr?.title ?? "Section"));
    }
  };
  walk(content, module);

  // Dedupe identical JSON blocks
  const seen = new Set<string>();
  for (const block of briefBlocks) {
    const key = block.replace(/\s+/g, " ");
    if (seen.has(key)) continue;
    seen.add(key);
    lines.push(block);
  }

  if (seen.size === 0) {
    lines.push("_No visual briefs found in this paper._");
    lines.push("");
  }
  return escapeMd(lines.join("\n").trim() + "\n");
}

/** True when content has at least one visual_brief / visual / images payload. */
export function contentHasVendorBriefs(content: PaperContent): boolean {
  const stack: unknown[] = [content];
  while (stack.length) {
    const node = stack.pop();
    const rec = asRecord(node);
    if (!rec) continue;
    if (rec.visual_brief || rec.visualBrief || rec.visual) return true;
    if (asArray(rec.images).length) return true;
    stack.push(...asArray(rec.parts), ...asArray(rec.sections), ...asArray(rec.questionGroups), ...asArray(rec.questions));
  }
  if (typeof content.document === "string") {
    return /visual\s*brief|visual_brief|"scenario"\s*:/i.test(content.document);
  }
  return false;
}

/** Minimal JSON for Kokoro / Listening Audio upload. */
export function contentAsTtsJson(content: PaperContent): {
  speakers: unknown[];
  script: { turns: unknown[] };
  type: "listening";
} {
  const speakers = asArray(content.speakers);
  const script = asRecord(content.script);
  let turns = script ? asArray(script.turns) : [];

  // Merged multi-part papers may nest parts with their own scripts
  if (!turns.length) {
    const parts = asArray(content.parts);
    const merged: unknown[] = [];
    const speakerMap = new Map<string, unknown>();
    for (const sp of speakers) {
      const rec = asRecord(sp);
      if (rec && rec.id != null) speakerMap.set(String(rec.id), sp);
    }
    for (const part of parts) {
      const p = asRecord(part);
      if (!p) continue;
      for (const sp of asArray(p.speakers)) {
        const rec = asRecord(sp);
        if (rec && rec.id != null && !speakerMap.has(String(rec.id))) {
          speakerMap.set(String(rec.id), sp);
        }
      }
      const pScript = asRecord(p.script);
      if (pScript) merged.push(...asArray(pScript.turns));
    }
    if (merged.length) turns = merged;
    if (!speakers.length && speakerMap.size) {
      return {
        type: "listening",
        speakers: [...speakerMap.values()],
        script: { turns },
      };
    }
  }

  return {
    type: "listening",
    speakers,
    script: { turns },
  };
}

/** Human-readable listening script (not for Kokoro unless JSON is used). */
export function contentAsListeningScriptMarkdown(content: PaperContent): string {
  const lines: string[] = [];
  const title =
    (typeof content.title === "string" && content.title) ||
    "Listening Script";
  lines.push(`# ${title} — Script`);
  lines.push("");
  lines.push(
    "_Teacher / production script. For audio synthesis use the TTS JSON download._",
  );
  lines.push("");

  const tts = contentAsTtsJson(content);
  const speakerMeta = new Map<string, string>();
  for (const sp of tts.speakers) {
    const rec = asRecord(sp);
    if (!rec || rec.id == null) continue;
    const id = String(rec.id);
    const role = typeof rec.role === "string" ? rec.role : "";
    const name = typeof rec.name === "string" ? rec.name : "";
    const accent = typeof rec.accent === "string" ? rec.accent : "";
    const gender = typeof rec.gender === "string" ? rec.gender : "";
    const bits = [name || id, role, accent, gender].filter(Boolean);
    speakerMeta.set(id, bits.join(", "));
  }

  if (speakerMeta.size) {
    lines.push("## Speakers");
    for (const [id, meta] of speakerMeta) {
      lines.push(`- **${id}** — ${meta}`);
    }
    lines.push("");
  }

  lines.push("## Turns");
  lines.push("");
  tts.script.turns.forEach((turn, i) => {
    const t = asRecord(turn);
    if (!t) return;
    const speaker = String(t.speaker ?? "?");
    const text = String(t.text ?? "");
    if (speaker.toUpperCase() === "PAUSE" || /\[PAUSE:/i.test(text)) {
      lines.push(`${i + 1}. *[PAUSE]* ${text}`);
    } else {
      lines.push(`${i + 1}. **${speaker}:** ${text}`);
    }
    lines.push("");
  });

  return escapeMd(lines.join("\n").trim() + "\n");
}

/** Very small Markdown → HTML for print/PDF (no external deps). */
export function markdownToPrintHtml(title: string, markdown: string): string {
  const escaped = markdown
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  const htmlBody = escaped
    .split("\n")
    .map((line) => {
      if (line.startsWith("# ")) return `<h1>${inlineMd(line.slice(2))}</h1>`;
      if (line.startsWith("## ")) return `<h2>${inlineMd(line.slice(3))}</h2>`;
      if (line.startsWith("### ")) return `<h3>${inlineMd(line.slice(4))}</h3>`;
      if (line.startsWith("- ")) return `<li>${inlineMd(line.slice(2))}</li>`;
      if (line.startsWith("```")) return "";
      if (!line.trim()) return "<br/>";
      return `<p>${inlineMd(line)}</p>`;
    })
    .join("\n");

  // Wrap consecutive <li> in <ul>
  const withLists = htmlBody.replace(
    /(<li>[\s\S]*?<\/li>)(\s*<li>[\s\S]*?<\/li>)*/g,
    (block) => `<ul>${block}</ul>`,
  );

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>${title.replace(/</g, "")}</title>
  <style>
    @page { margin: 18mm; }
    body { font-family: Georgia, "Times New Roman", serif; font-size: 12pt; line-height: 1.45; color: #111; max-width: 720px; margin: 0 auto; padding: 24px; }
    h1 { font-size: 20pt; margin: 0 0 12pt; }
    h2 { font-size: 14pt; margin: 18pt 0 8pt; border-bottom: 1px solid #ccc; padding-bottom: 4pt; }
    h3 { font-size: 12pt; margin: 14pt 0 6pt; }
    p, li { margin: 0 0 6pt; }
    ul { margin: 0 0 10pt 1.2em; padding: 0; }
    em, i { color: #444; }
    strong { font-weight: 700; }
    @media print {
      body { padding: 0; }
      .no-print { display: none !important; }
    }
  </style>
</head>
<body>
  <p class="no-print" style="font-family: system-ui, sans-serif; font-size: 11px; color: #666;">
    Use your browser Print dialog → Save as PDF.
  </p>
  ${withLists}
</body>
</html>`;
}

function inlineMd(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/_(.+?)_/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

/** Map common Unicode punctuation / symbols to ASCII for Helvetica Type1 PDFs. */
const PDF_CHAR_MAP: Record<number, string> = {
  0x00a0: " ", // nbsp
  0x00a9: "(c)",
  0x00ae: "(R)",
  0x00b0: " deg",
  0x00b7: "-", // middle dot
  0x00d7: "x",
  0x2010: "-",
  0x2011: "-",
  0x2012: "-",
  0x2013: "-", // en dash
  0x2014: "-", // em dash
  0x2015: "-",
  0x2018: "'",
  0x2019: "'",
  0x201a: "'",
  0x201c: '"',
  0x201d: '"',
  0x201e: '"',
  0x2022: "-", // bullet
  0x2023: "-",
  0x2026: "...",
  0x2032: "'",
  0x2033: '"',
  0x2044: "/",
  0x20ac: "EUR",
  0x2122: "(TM)",
  0x2190: "<-",
  0x2192: "->",
  0x2194: "<->",
  0x21d2: "=>",
  0x2212: "-", // minus
  0x2260: "!=",
  0x2264: "<=",
  0x2265: ">=",
  0x00b1: "+/-",
};

function toPdfAscii(text: string): string {
  // Strip accents: café → cafe (Helvetica Type1 can't do Unicode)
  const decomposed = text.normalize("NFD").replace(/\p{M}/gu, "");
  let out = "";
  for (const ch of decomposed) {
    const code = ch.codePointAt(0) ?? 0;
    if (code >= 0x20 && code <= 0x7e) {
      out += ch;
      continue;
    }
    if (code === 0x09) {
      out += " ";
      continue;
    }
    if (code === 0x0a || code === 0x0d) {
      out += " ";
      continue;
    }
    const mapped = PDF_CHAR_MAP[code];
    if (mapped !== undefined) {
      out += mapped;
      continue;
    }
    // Soft hyphen / zero-width
    if (code === 0x00ad || code === 0x200b || code === 0x200c || code === 0x200d || code === 0xfeff) {
      continue;
    }
    out += "-";
  }
  return out;
}

function pdfEscape(text: string): string {
  return toPdfAscii(text)
    .replace(/\\/g, "\\\\")
    .replace(/\(/g, "\\(")
    .replace(/\)/g, "\\)");
}

function markdownToPlainLines(markdown: string): string[] {
  const out: string[] = [];
  for (const raw of markdown.replace(/\r\n/g, "\n").split("\n")) {
    let line = raw
      .replace(/^#{1,6}\s+/, "")
      // ASCII list marker — Unicode bullets become "?" in Helvetica PDFs
      .replace(/^\s*[-*•▪▫◦‣]\s+/, "- ")
      .replace(/\*\*(.+?)\*\*/g, "$1")
      .replace(/\*(.+?)\*/g, "$1")
      .replace(/_(.+?)_/g, "$1")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/```.*/g, "");
    if (line.startsWith("```")) continue;
    line = toPdfAscii(line);
    // Soft-wrap long lines for PDF page width (~90 chars at 10pt)
    const max = 90;
    while (line.length > max) {
      let breakAt = line.lastIndexOf(" ", max);
      if (breakAt < 40) breakAt = max;
      out.push(line.slice(0, breakAt));
      line = line.slice(breakAt).trimStart();
    }
    out.push(line);
  }
  return out;
}

/**
 * Dependency-free multi-page text PDF (Helvetica).
 * Good enough for practice-paper downloads until a richer export service exists.
 */
export function markdownToPdfBlob(title: string, markdown: string): Blob {
  const lines = [
    title.replace(/\.pdf$/i, ""),
    "",
    ...markdownToPlainLines(markdown),
  ];
  const pageWidth = 612; // US Letter points
  const pageHeight = 792;
  const marginX = 54;
  const marginTop = 54;
  const marginBottom = 54;
  const fontSize = 10;
  const leading = 14;
  const usable = pageHeight - marginTop - marginBottom;
  const linesPerPage = Math.max(1, Math.floor(usable / leading));

  const pages: string[][] = [];
  for (let i = 0; i < lines.length; i += linesPerPage) {
    pages.push(lines.slice(i, i + linesPerPage));
  }
  if (!pages.length) pages.push([""]);

  const objects: string[] = [];
  const addObj = (body: string): number => {
    objects.push(body);
    return objects.length; // 1-based id
  };

  const fontId = addObj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>");
  const contentIds: number[] = [];
  const pageIds: number[] = [];

  for (const pageLines of pages) {
    const contentParts: string[] = [
      "BT",
      `/F1 ${fontSize} Tf`,
      `${leading} TL`,
      `${marginX} ${pageHeight - marginTop} Td`,
    ];
    pageLines.forEach((line, idx) => {
      const safe = pdfEscape(line);
      if (idx === 0) contentParts.push(`(${safe}) Tj`);
      else contentParts.push(`T* (${safe}) Tj`);
    });
    contentParts.push("ET");
    const stream = contentParts.join("\n");
    contentIds.push(
      addObj(
        `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`,
      ),
    );
  }

  // Pages must reference Kids; build page objects after contents exist
  for (let i = 0; i < pages.length; i++) {
    pageIds.push(
      addObj(
        `<< /Type /Page /Parent 0 0 R /MediaBox [0 0 ${pageWidth} ${pageHeight}] ` +
          `/Contents ${contentIds[i]} 0 R /Resources << /Font << /F1 ${fontId} 0 R >> >> >>`,
      ),
    );
  }

  const kids = pageIds.map((id) => `${id} 0 R`).join(" ");
  const pagesId = addObj(
    `<< /Type /Pages /Kids [ ${kids} ] /Count ${pageIds.length} >>`,
  );
  // Patch Parent references (Pages id now known)
  for (let i = 0; i < pageIds.length; i++) {
    const id = pageIds[i]!;
    objects[id - 1] = objects[id - 1]!.replace(
      "/Parent 0 0 R",
      `/Parent ${pagesId} 0 R`,
    );
  }

  const catalogId = addObj(`<< /Type /Catalog /Pages ${pagesId} 0 R >>`);

  let pdf = "%PDF-1.4\n";
  const offsets: number[] = [0];
  for (let i = 0; i < objects.length; i++) {
    offsets.push(pdf.length);
    pdf += `${i + 1} 0 obj\n${objects[i]}\nendobj\n`;
  }
  const xrefPos = pdf.length;
  pdf += `xref\n0 ${objects.length + 1}\n`;
  pdf += "0000000000 65535 f \n";
  for (let i = 1; i <= objects.length; i++) {
    pdf += `${String(offsets[i]).padStart(10, "0")} 00000 n \n`;
  }
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root ${catalogId} 0 R >>\n`;
  pdf += `startxref\n${xrefPos}\n%%EOF`;

  return new Blob([pdf], { type: "application/pdf" });
}

export function downloadPdfFile(filename: string, title: string, markdown: string): void {
  const name = filename.endsWith(".pdf") ? filename : `${filename}.pdf`;
  const blob = markdownToPdfBlob(title, markdown);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * Open the system print dialog via a hidden iframe + blob URL (no popup / noopener).
 * User should choose "Save as PDF" in the dialog.
 */
export function openPrintPdf(title: string, markdown: string): void {
  const html = markdownToPrintHtml(title, markdown);
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);

  const iframe = document.createElement("iframe");
  iframe.setAttribute("title", title);
  iframe.style.position = "fixed";
  iframe.style.right = "0";
  iframe.style.bottom = "0";
  iframe.style.width = "0";
  iframe.style.height = "0";
  iframe.style.border = "0";
  iframe.style.opacity = "0";
  iframe.style.pointerEvents = "none";
  document.body.appendChild(iframe);

  const cleanup = () => {
    try {
      URL.revokeObjectURL(url);
    } catch {
      // ignore
    }
    try {
      iframe.remove();
    } catch {
      // ignore
    }
  };

  iframe.onload = () => {
    try {
      const frameWindow = iframe.contentWindow;
      if (!frameWindow) {
        cleanup();
        throw new Error("Could not access print frame.");
      }
      frameWindow.focus();
      // slight delay helps Chrome layout before print
      setTimeout(() => {
        try {
          frameWindow.print();
        } finally {
          // Delay cleanup so the print dialog can read the document
          setTimeout(cleanup, 60_000);
        }
      }, 100);
    } catch (err) {
      cleanup();
      throw err;
    }
  };

  iframe.src = url;
}

/**
 * One-click .pdf download, then also open print dialog as a formatted fallback.
 * Returns a short user-facing tip string for a toast.
 */
export function exportPdfWithPrintFallback(
  filename: string,
  title: string,
  markdown: string,
): string {
  downloadPdfFile(filename, title, markdown);
  try {
    openPrintPdf(title, markdown);
  } catch {
    // File download already succeeded; print is optional formatting aid
  }
  return 'PDF downloaded (ASCII-safe text). If a print dialog opens, choose "Save as PDF" for full Unicode formatting.';
}
