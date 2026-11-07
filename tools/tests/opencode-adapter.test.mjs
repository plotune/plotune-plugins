// Tests for tools/opencode-adapter.js and every plugin's copy of it.
// Run: node --test tools/tests/opencode-adapter.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../..");
const template = path.join(repo, "tools", "opencode-adapter.js");
const pluginsDir = path.join(repo, "plugins");

const pluginDirs = () =>
  fs.readdirSync(pluginsDir, { withFileTypes: true })
    .filter((d) => d.isDirectory() && fs.existsSync(path.join(pluginsDir, d.name, "index.js")))
    .map((d) => path.join(pluginsDir, d.name));

// A throwaway plugin directory with a copy of the adapter, so tests control the skills.
function scratchPlugin(skills) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "oc-adapter-"));
  fs.copyFileSync(template, path.join(dir, "index.js"));
  fs.writeFileSync(path.join(dir, "package.json"), JSON.stringify({ name: "scratch", version: "0.0.1" }));
  for (const [name, body] of Object.entries(skills)) {
    fs.mkdirSync(path.join(dir, "skills", name), { recursive: true });
    fs.writeFileSync(path.join(dir, "skills", name, "SKILL.md"), body);
  }
  return dir;
}

const load = async (dir) => (await import(pathToFileURL(path.join(dir, "index.js")).href + `?t=${Math.random()}`));

function fakeCtx() {
  const added = [];
  return {
    added,
    skill: { transform: async (fn) => fn({ add: (s) => added.push(s) }) },
    session: { hook: () => {} },
  };
}

test("every plugin that ships index.js has an identical copy of the adapter", () => {
  const dirs = pluginDirs();
  assert.ok(dirs.length > 0, "expected at least one plugin with index.js");
  const expected = fs.readFileSync(template, "utf8");
  for (const dir of dirs) {
    assert.equal(fs.readFileSync(path.join(dir, "index.js"), "utf8"), expected, `${dir} adapter differs from template`);
  }
});

test("default export has the package name as id and a setup function", async () => {
  const dir = scratchPlugin({ "a-skill": "---\nname: a-skill\ndescription: Use it.\n---\nbody" });
  const mod = await load(dir);
  assert.equal(mod.default.id, "scratch");
  assert.equal(typeof mod.default.setup, "function");
});

test("setup registers every skill with id, name, description, path and body without frontmatter", async () => {
  const dir = scratchPlugin({
    "one": "---\nname: one\ndescription: First skill.\n---\n# One\nBody one",
    "two": "---\nname: two\ndescription: >\n  Second\n  skill.\n---\n# Two",
  });
  const ctx = fakeCtx();
  await (await load(dir)).default.setup(ctx);
  const byId = Object.fromEntries(ctx.added.map((s) => [s.id, s]));
  assert.deepEqual(Object.keys(byId).sort(), ["one", "two"]);
  assert.equal(byId.one.name, "one");
  assert.equal(byId.one.description, "First skill.");
  assert.equal(byId.one.path, path.join(dir, "skills", "one", "SKILL.md"));
  assert.ok(byId.one.content.includes("Body one"));
  assert.ok(!byId.one.content.includes("description:"));
  assert.equal(byId.two.description, "Second skill.");
});

test("skills without SKILL.md and hidden directories are skipped", async () => {
  const dir = scratchPlugin({ "real": "---\nname: real\ndescription: d\n---\nx" });
  fs.mkdirSync(path.join(dir, "skills", "empty"));
  fs.mkdirSync(path.join(dir, "skills", ".hidden"));
  fs.writeFileSync(path.join(dir, "skills", ".hidden", "SKILL.md"), "---\nname: h\ndescription: d\n---\n");
  const ctx = fakeCtx();
  await (await load(dir)).default.setup(ctx);
  assert.deepEqual(ctx.added.map((s) => s.id), ["real"]);
});

test("a skill the host rejects does not stop the others or throw", async () => {
  const dir = scratchPlugin({
    "aaa": "---\nname: aaa\ndescription: d\n---\nx",
    "bbb": "---\nname: bbb\ndescription: d\n---\nx",
  });
  const added = [];
  const ctx = {
    skill: { transform: async (fn) => fn({ add: (s) => { if (s.id === "aaa") throw new Error("schema"); added.push(s.id); } }) },
    session: { hook: () => {} },
  };
  const originalError = console.error;
  console.error = () => {};
  try {
    await (await load(dir)).default.setup(ctx);
  } finally {
    console.error = originalError;
  }
  assert.deepEqual(added, ["bbb"]);
});

test("setup returns quietly for a host context without the skill domain (V1 shape)", async () => {
  const dir = scratchPlugin({ "a": "---\nname: a\ndescription: d\n---\nx" });
  await (await load(dir)).default.setup({});
  await (await load(dir)).default.setup(undefined);
});

test("missing skills directory registers nothing and does not throw", async () => {
  const dir = scratchPlugin({});
  const ctx = fakeCtx();
  await (await load(dir)).default.setup(ctx);
  assert.deepEqual(ctx.added, []);
});

test("V1 config hook adds the skills directory once, for object and array config shapes", async () => {
  const dir = scratchPlugin({ "a": "---\nname: a\ndescription: d\n---\nx" });
  const hooks = await (await load(dir)).default.server({});
  const skillsDir = path.join(dir, "skills");

  const objectConfig = {};
  await hooks.config(objectConfig);
  await hooks.config(objectConfig);
  assert.deepEqual(objectConfig.skills.paths, [skillsDir]);

  const arrayConfig = { skills: ["/other"] };
  await hooks.config(arrayConfig);
  await hooks.config(arrayConfig);
  assert.deepEqual(arrayConfig.skills, ["/other", skillsDir]);
});

test("an unreadable SKILL.md is skipped and the other skills still register", async () => {
  const dir = scratchPlugin({ "good": "---\nname: good\ndescription: d\n---\nx" });
  // a directory where SKILL.md should be: existsSync is true but reading it throws EISDIR
  fs.mkdirSync(path.join(dir, "skills", "broken", "SKILL.md"), { recursive: true });
  const ctx = fakeCtx();
  const originalError = console.error;
  console.error = () => {};
  try {
    await (await load(dir)).default.setup(ctx);
  } finally {
    console.error = originalError;
  }
  assert.deepEqual(ctx.added.map((s) => s.id), ["good"]);
});

test("a missing package.json does not crash the plugin; the id falls back to the directory name", async () => {
  const dir = scratchPlugin({ "a": "---\nname: a\ndescription: d\n---\nx" });
  fs.unlinkSync(path.join(dir, "package.json"));
  const mod = await load(dir);
  assert.equal(mod.default.id, path.basename(dir));
  const ctx = fakeCtx();
  await mod.default.setup(ctx);
  assert.deepEqual(ctx.added.map((s) => s.id), ["a"]);
});

test("a symlinked skill directory is registered", async () => {
  const dir = scratchPlugin({});
  const target = fs.mkdtempSync(path.join(os.tmpdir(), "oc-skill-target-"));
  fs.writeFileSync(path.join(target, "SKILL.md"), "---\nname: linked\ndescription: d\n---\nx");
  fs.mkdirSync(path.join(dir, "skills"), { recursive: true });
  fs.symlinkSync(target, path.join(dir, "skills", "linked"), "dir");
  const ctx = fakeCtx();
  await (await load(dir)).default.setup(ctx);
  assert.deepEqual(ctx.added.map((s) => s.id), ["linked"]);
});

test("each real plugin adapter registers exactly its own skills", async () => {
  for (const dir of pluginDirs()) {
    const skillNames = fs.readdirSync(path.join(dir, "skills"), { withFileTypes: true })
      .filter((d) => d.isDirectory()).map((d) => d.name).sort();
    const ctx = fakeCtx();
    await (await load(dir)).default.setup(ctx);
    assert.deepEqual(ctx.added.map((s) => s.id).sort(), skillNames, path.basename(dir));
  }
});
