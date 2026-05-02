/**
 * delegate.mjs — stdout-delegate helper for skill scripts (Mode D)
 *
 * Scripts call llmInvoke() to emit __LLM_DELEGATE__ directives.
 * The host agent (Claude Code, or any Mode-D-aware provider) reads the
 * script's stdout and executes each directive: calls the LLM, writes the
 * result to `out`.
 *
 * Copy this file into your skill's scripts/ directory, or inline the single
 * process.stdout.write call — no external dependencies needed.
 *
 * Usage:
 *   import { llmInvoke } from './delegate.mjs';
 *
 *   llmInvoke({
 *     prompt: `Summarise this diff in one sentence: ${diffText}`,
 *     out: 'tmp/summary.txt',
 *   });
 *
 *   llmInvoke({
 *     prompt: 'Classify as feat/fix/chore. Reply with JSON: {label: ...}',
 *     json: true,
 *     out: 'tmp/label.json',
 *   });
 */

/**
 * Emit a single __LLM_DELEGATE__ directive to stdout.
 *
 * The host agent reads this after the script exits and:
 *   1. Calls the LLM with `prompt` (prepending `system` if given).
 *   2. If `json: true`, requests JSON output.
 *   3. Writes the response to `out` (creating parent dirs as needed).
 *
 * @param {object} options
 * @param {string}  options.prompt    - Instruction for the LLM.
 * @param {string}  [options.out]     - File path to write the LLM response into.
 * @param {string}  [options.system]  - System prompt to prepend.
 * @param {boolean} [options.json]    - Request JSON output from the LLM.
 * @param {string}  [options.id]      - Label to reference this result by name.
 */
export function llmInvoke({ prompt, out, system, json = false, id } = {}) {
  const d = { prompt };
  if (out    != null) d.out    = out;
  if (system != null) d.system = system;
  if (json)           d.json   = true;
  if (id     != null) d.id     = id;
  process.stdout.write(`__LLM_DELEGATE__: ${JSON.stringify(d)}\n`);
}
