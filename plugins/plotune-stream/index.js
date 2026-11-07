// OpenCode adapter for a Plotune plugin: registers this plugin's skills/ directory.
//
// This file is generated: edit tools/opencode-adapter.js and run tools/sync_opencode.py,
// never a plugin's index.js directly (tools/check_manifests.py and the node tests
// verify every copy is identical to this template).
//
// No dependencies, so it works whether OpenCode loads it as a V1 plugin (named export with
// a `config` hook) or a V2 plugin (default export with `setup(ctx)`). MCP servers are not
// registered here: add them with `opencode mcp add` or in opencode.json (see the README).

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const skillsDir = path.join(root, "skills");
const pluginId = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8")).name;

// Minimal frontmatter reader: plain, quoted and block-scalar values, indented continuations.
function splitFrontmatter(text) {
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)([\s\S]*)$/);
  if (!match) return { data: {}, body: text };
  const data = {};
  let last = null;
  for (const raw of match[1].split("\n")) {
    const line = raw.replace(/\r$/, "");
    const colon = line.indexOf(":");
    if (colon > 0 && !/^\s/.test(line)) {
      last = line.slice(0, colon).trim();
      const value = line.slice(colon + 1).trim();
      data[last] = /^[>|][+-]?$/.test(value) ? "" : value;
    } else if (last !== null && line.trim() !== "") {
      data[last] = `${data[last]} ${line.trim()}`.trim();
    }
  }
  for (const key of Object.keys(data)) {
    data[key] = data[key].replace(/^(["'])([\s\S]*)\1$/, "$2");
  }
  return { data, body: match[2] };
}

function readSkills(dir = skillsDir) {
  if (!fs.existsSync(dir)) return [];
  const skills = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (!entry.isDirectory() || entry.name.startsWith(".")) continue;
    const file = path.join(dir, entry.name, "SKILL.md");
    if (!fs.existsSync(file)) continue;
    const { data, body } = splitFrontmatter(fs.readFileSync(file, "utf8"));
    skills.push({
      id: entry.name,
      name: data.name || entry.name,
      ...(data.description ? { description: data.description } : {}),
      path: file,
      content: body,
    });
  }
  return skills;
}

// V1: the host calls config(config); add the skills directory to whichever shape it uses.
export const PlotunePlugin = async () => ({
  config: async (config) => {
    if (Array.isArray(config.skills)) {
      if (!config.skills.includes(skillsDir)) config.skills.push(skillsDir);
      return;
    }
    config.skills = config.skills || {};
    config.skills.paths = config.skills.paths || [];
    if (!config.skills.paths.includes(skillsDir)) config.skills.paths.push(skillsDir);
  },
});

// V2: register each skill natively. A skill the host rejects is skipped, never fatal:
// throwing from the transform would disable the whole plugin.
async function setup(ctx) {
  if (!ctx || !ctx.skill || typeof ctx.skill.transform !== "function") return;
  const skills = readSkills();
  await ctx.skill.transform((draft) => {
    for (const skill of skills) {
      try {
        draft.add(skill);
      } catch (err) {
        console.error(`[${pluginId}] skill "${skill.id}" rejected by host, skipping:`, err);
      }
    }
  });
}

export default { id: pluginId, server: PlotunePlugin, setup };
