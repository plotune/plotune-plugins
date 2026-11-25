"""The file-handoff format (skills/requirements-cycle/roles/file-handoff.md): the example validates against
schema/handoff-records.schema.json, and the checks a broken file must fail actually fail.
Run: python -m unittest discover -s tests -v
"""
import copy
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'schema' / 'handoff-records.schema.json').read_text(encoding='utf-8'))
DOC = (ROOT / 'skills' / 'requirements-cycle' / 'roles' / 'file-handoff.md').read_text(encoding='utf-8')


def resolve(schema, node):
    while '$ref' in node:
        node = schema['$defs'][node['$ref'].rsplit('/', 1)[1]]
    return node


def errors(schema, node, value, where='$'):
    """The subset of JSON Schema this format uses: type, const, enum, pattern, minLength, maxLength, minItems,
    required, properties, additionalProperties false, items, $ref to $defs, oneOf."""
    node = resolve(schema, node)
    out = []
    if 'oneOf' in node:
        matches = [opt for opt in node['oneOf'] if not errors(schema, opt, value, where)]
        return [] if len(matches) == 1 else [f'{where}: matches {len(matches)} of oneOf']
    types = node.get('type')
    if types:
        types = types if isinstance(types, list) else [types]
        ok = {'object': dict, 'array': list, 'string': str, 'boolean': bool, 'null': type(None)}
        good = any((t == 'integer' and isinstance(value, int) and not isinstance(value, bool))
                   or (t == 'number' and isinstance(value, (int, float)) and not isinstance(value, bool))
                   or (t in ok and isinstance(value, ok[t])) for t in types)
        if not good:
            return [f'{where}: expected {types}']
    if 'const' in node and value != node['const']:
        out.append(f'{where}: must be {node["const"]!r}')
    if 'enum' in node and value not in node['enum']:
        out.append(f'{where}: {value!r} not in {node["enum"]}')
    if isinstance(value, str):
        if 'pattern' in node and not re.search(node['pattern'], value):
            out.append(f'{where}: does not match {node["pattern"]}')
        if len(value) < node.get('minLength', 0) or len(value) > node.get('maxLength', 10 ** 9):
            out.append(f'{where}: length')
    if isinstance(value, list):
        if len(value) < node.get('minItems', 0):
            out.append(f'{where}: too few items')
        for i, item in enumerate(value):
            out += errors(schema, node.get('items', {}), item, f'{where}[{i}]')
    if isinstance(value, dict):
        for key in node.get('required', []):
            if key not in value:
                out.append(f'{where}: missing {key}')
        props = node.get('properties', {})
        for key, item in value.items():
            if key in props:
                out += errors(schema, props[key], item, f'{where}.{key}')
            elif node.get('additionalProperties') is False:
                out.append(f'{where}: unexpected {key}')
    return out


def example():
    blocks = re.findall(r'```json\n(.*?)\n```', DOC, re.S)
    assert len(blocks) == 1, 'file-handoff.md has exactly one json example'
    return json.loads(blocks[0])


class FileHandoffTest(unittest.TestCase):
    def test_example_validates(self):
        self.assertEqual(errors(SCHEMA, SCHEMA, example()), [])

    def test_broken_files_fail(self):
        base = example()
        cases = {
            'no author role': lambda d: d['author'].pop('role'),
            'role outside the cycle': lambda d: d['author'].update(role='orchestrator'),
            'wrong format': lambda d: d.update(format='plotune-handoff-records/2'),
            'requirement without criteria': lambda d: d['requirements'][0].pop('criteria'),
            'requirement state other than Draft': lambda d: d['requirements'][0].update(state='Approved'),
            'test case without a requirement': lambda d: d['testCases'][0].pop('requirement'),
            'decision group unknown': lambda d: d['decisions'][0].update(group='later'),
            'parameter id format': lambda d: d['parameters'][0].update(id='P7'),
            'unexpected field': lambda d: d.update(approved=True),
        }
        for name, change in cases.items():
            with self.subTest(name):
                broken = copy.deepcopy(base)
                change(broken)
                self.assertNotEqual(errors(SCHEMA, SCHEMA, broken), [], name)

    def test_keys_are_unique_and_references_resolve(self):
        d = example()
        keys = [r['key'] for r in d['requirements']]
        self.assertEqual(len(keys), len(set(keys)))
        params = {p['id'] for p in d['parameters']}
        for tc in d['testCases']:
            ref = tc['requirement']
            self.assertTrue(ref.get('key') in keys or 'id' in ref, tc['key'])
        # Criteria name declared parameters only.
        for r in d['requirements']:
            for p in re.findall(r'\bP-\d{2,3}\b', r['criteria']):
                self.assertIn(p, params, r['key'])


if __name__ == '__main__':
    unittest.main()
