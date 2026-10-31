import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { auditRuntime } from '../../scripts/audit-standard-runtime.mjs';

test('current entries reach only their runtime assets and configured questions', () => {
    const { entries, files } = auditRuntime();
    assert.equal(entries.length, 3);
    assert.ok(files.includes('assets/js/shared/questionLoader.js'));
    assert.ok(files.includes('assets/js/actual/app.js'));
    assert.ok(files.includes('language/JLPT_N2/data/JLPT_N2_LK_Ch.json'));
    assert.ok(files.every(file => !/(^|\/)(tests|docs|prompt|old|test_version)(\/|$)/.test(file)));
    assert.ok(!files.includes('language/JLPT_N2/questionLoader.js'));
});

test('missing transitive assets and dependencies on history fail the audit', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'standard-runtime-'));
    try {
        const manifest = { schemaVersion: 1, entries: ['index.html'], legacyFiles: ['legacy.js'] };
        fs.writeFileSync(path.join(root, 'index.html'), '<script type="module" src="app.js"></script>');
        fs.writeFileSync(path.join(root, 'app.js'), "import './missing.js';");
        assert.throws(() => auditRuntime(root, manifest), /ENOENT/);
        fs.writeFileSync(path.join(root, 'missing.js'), "import './legacy.js';");
        fs.writeFileSync(path.join(root, 'legacy.js'), '// preserved development history');
        assert.throws(() => auditRuntime(root, manifest), /開発履歴/);
        fs.writeFileSync(path.join(root, 'missing.js'), '// no more dependencies');
        assert.deepEqual(auditRuntime(root, manifest).files, ['app.js', 'index.html', 'missing.js']);
        fs.writeFileSync(path.join(root, 'index.html'), '<link rel="stylesheet" href="missing.css">');
        assert.throws(() => auditRuntime(root, manifest), /ENOENT/);
    } finally { fs.rmSync(root, { recursive: true, force: true }); }
});
