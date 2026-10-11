/**
 * Assemble the Isla AI demo film — final cut.
 *
 * Timeline (must total exactly 60.00s):
 *   0.0  H3 open          5.0s   generated hero, MiniMax-H3 2K
 *   5.0  problem          7.0s   CSS motion graphic
 *  12.0  egress guard    14.0s   REAL product, verified click
 *  26.0  fraud & AML     13.0s   REAL product, verified click
 *  39.0  DPA copilot     10.0s   REAL product, verified click
 *  49.0  proof numbers    7.0s   CSS motion graphic
 *  56.0  H3 close         4.0s   generated hero, MiniMax-H3 2K
 *
 * Audio is a separate graph: ten voiceover clips placed at fixed offsets over
 * a music bed that ducks while anyone is speaking. Ducking is done with
 * sidechaincompress rather than hand-tuned gain, so the level follows the
 * narration instead of hoping the timings line up.
 *
 *   node apps/web/video/build.mjs
 */
import { readdirSync, mkdirSync, statSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SHOTS = resolve(HERE, 'shots');
const H3 = resolve(HERE, 'h3');
const AUDIO = resolve(HERE, 'audio');
const OUT = resolve(HERE, 'out');
const FFMPEG = process.env.FFMPEG_PATH || 'ffmpeg';
const FFPROBE = process.env.FFPROBE_PATH || 'ffprobe';

const ff = (args) => {
  try {
    return execFileSync(FFMPEG, args, { stdio: ['ignore', 'pipe', 'pipe'] });
  } catch (e) {
    // Surface ffmpeg's own diagnosis; a raw Buffer dump is unreadable and
    // hides the one line that says which filter or input is at fault.
    const log = String(e.stderr || '').trim().split(/\r?\n/);
    const useful = log.filter((l) => /error|invalid|no such|failed|not found|unable/i.test(l));
    console.error('\nffmpeg failed:\n' + (useful.length ? useful.slice(-14).join('\n') : log.slice(-14).join('\n')));
    throw new Error('ffmpeg exited non-zero');
  }
};
const dur = (f) => parseFloat(String(execFileSync(FFPROBE,
  ['-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', f],
  { stdio: ['ignore', 'pipe', 'pipe'] })).trim());

const shot = (n) => resolve(SHOTS, n, readdirSync(resolve(SHOTS, n)).find((f) => f.endsWith('.webm')));

// ── the edit ────────────────────────────────────────────────────────────────
const CUT = [
  { in: resolve(H3, 'open.mp4'),        ms: 5000,  tag: 'H3 open' },
  { in: shot('02-problem'),             ms: 7000,  tag: 'problem' },
  { in: shot('03-egress'),              ms: 14000, tag: 'egress  [PRODUCT]' },
  { in: shot('04-risk'),                ms: 13000, tag: 'risk    [PRODUCT]' },
  { in: shot('05-copilot'),             ms: 10000, tag: 'copilot [PRODUCT]' },
  { in: shot('06-numbers'),             ms: 7000,  tag: 'numbers' },
  { in: resolve(H3, 'close.mp4'),       ms: 4000,  tag: 'H3 close' },
];

const TOTAL = CUT.reduce((n, c) => n + c.ms, 0) / 1000;

// Voiceover: [file, startSeconds]
const VO = [
  ['vo-01-problem.mp3',    5.2],
  ['vo-02-need.mp3',      10.2],
  ['vo-03-redact.mp3',    13.0],
  ['vo-04-verify.mp3',    18.4],
  ['vo-05-block.mp3',     22.8],
  ['vo-06-critical.mp3',  27.4],
  ['vo-07-gap.mp3',       33.9],
  ['vo-08-hours.mp3',     39.6],
  ['vo-09-extractive.mp3',44.2],
  ['vo-10-close.mp3',     50.2],
];

mkdirSync(OUT, { recursive: true });

console.log('Picture');
for (const c of CUT) {
  if (!statSync(c.in)) { console.error(`  MISSING ${c.tag}`); process.exit(1); }
  console.log(`  ${c.tag.padEnd(18)} ${(c.ms / 1000).toFixed(1)}s  source ${dur(c.in).toFixed(2)}s`);
}
console.log(`  ${'TOTAL'.padEnd(18)} ${TOTAL.toFixed(1)}s\n`);

console.log('Voiceover');
let voWarn = 0;
for (const [f, at] of VO) {
  const p = resolve(AUDIO, f);
  const d = dur(p);
  const end = at + d;
  const flag = end > TOTAL - 0.05 ? ' <-- overruns' : '';
  if (flag) voWarn += 1;
  console.log(`  ${f.padEnd(22)} @${at.toFixed(1)}s  ${d.toFixed(2)}s  ends ${end.toFixed(2)}s${flag}`);
}
if (voWarn) console.log(`  ${voWarn} line(s) run past the end - check placement\n`);

// ── video graph ─────────────────────────────────────────────────────────────
// Every input is scaled to the delivery raster, pinned to 25fps and hard-cut to
// its slot. Trimming to an exact duration is what makes the total land on 60.
const vparts = [];
const vlabels = [];
CUT.forEach((c, i) => {
  vparts.push(`[${i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,` +
              `pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=010F14,` +
              `fps=25,format=yuv420p,trim=duration=${(c.ms / 1000).toFixed(3)},setpts=PTS-STARTPTS[v${i}]`);
  vlabels.push(`[v${i}]`);
});
const videoGraph = `${vparts.join(';')};${vlabels.join('')}concat=n=${CUT.length}:v=1:a=0[vout]`;

// ── audio graph ─────────────────────────────────────────────────────────────
// Inputs are laid out as [0..6] picture, [7..16] voiceover, [17] bed. The voice
// offsets below are positions in VO, NOT ffmpeg input numbers - forget the
// offset and the graph binds to the video files.
const PIC = CUT.length;
const aparts = [];
const alabels = [];
VO.forEach(([, at], i) => {
  const ms = Math.round(at * 1000);
  aparts.push(`[${PIC + i}:a]adelay=${ms}|${ms}[v${i}]`);
  alabels.push(`[v${i}]`);
});
aparts.push(`${alabels.join('')}amix=inputs=${VO.length}:normalize=0:dropout_transition=0[vox]`);

const bedIdx = PIC + VO.length;
aparts.push(`[${bedIdx}:a]atrim=duration=${TOTAL},asetpts=PTS-STARTPTS,volume=0.30[bed]`);
aparts.push(`[vox]asplit=2[vox_mix][vox_key]`);
aparts.push(`[bed][vox_key]sidechaincompress=threshold=0.05:ratio=9:attack=20:release=380[bedduck]`);
aparts.push(`[bedduck][vox_mix]amix=inputs=2:normalize=0:dropout_transition=0,` +
            `alimiter=limit=0.95,atrim=duration=${TOTAL}[aout]`);

const silent = OUT + '/concat.txt';
const { writeFileSync } = await import('node:fs');
writeFileSync(silent, CUT.map((c) => `file '${c.in.replace(/\\/g, '/')}'`).join('\n'), 'utf8');
void silent;

// ── render ──────────────────────────────────────────────────────────────────
// One filter graph holds both halves: the picture chain consumes inputs 0..6,
// the audio chain consumes the ten voice clips (7..16) and the bed (17).
console.log('Rendering...');
const combined = `${videoGraph};${aparts.join(';')}`;

const args = ['-y'];
CUT.forEach((c) => args.push('-i', c.in));
VO.forEach(([f]) => args.push('-i', resolve(AUDIO, f)));
args.push('-i', resolve(AUDIO, 'bed.mp3'));
args.push(
  '-filter_complex', combined,
  '-map', '[vout]', '-map', '[aout]',
  '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
  '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '4.1',
  '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2',
  '-movflags', '+faststart',
  '-t', TOTAL.toFixed(3),
  resolve(OUT, 'ISLA-AI-demo-60s.mp4'),
);
ff(args);

const final = resolve(OUT, 'ISLA-AI-demo-60s.mp4');
const got = dur(final);
console.log(`\n  FINAL  ${final}`);
console.log(`  ${got.toFixed(2)}s  ${(statSync(final).size / 1024 / 1024).toFixed(2)} MB  1920x1080 h264+aac`);
console.log(Math.abs(got - 60) <= 0.10 ? '  length: on target' : `  length: OFF by ${(got - 60).toFixed(2)}s`);