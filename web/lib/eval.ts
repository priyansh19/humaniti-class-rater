// Primary LOO results copied from docs/EVAL.md (n = 10; one class = 10 points). Secondary and superseded variants live in the doc.
export const EVAL_SUMMARY: Array<{ variant: string; exact: number; within1: number; note?: string }> = [
  { variant: "Majority baseline (always Poor)", exact: 40, within1: 40, note: "reference" },
  { variant: "Transcript only (hosted demo)", exact: 20, within1: 60 },
  { variant: "Transcript + audio", exact: 30, within1: 70 },
  { variant: "Transcript + audio + frames", exact: 30, within1: 70 },
  { variant: "Full, ASR transcript (no VTT)", exact: 50, within1: 100, note: "best; small n" },
];
export const EVAL_DATE = "Oct 2026";
