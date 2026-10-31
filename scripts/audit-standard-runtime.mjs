import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

// This reports dependencies only. It never copies to public or publishes files.
export function auditRuntime(root = fileURLToPath(new URL('../prototype/', import.meta.url)), definition) {
    root = fs.realpathSync(root);
    const manifest = definition ?? JSON.parse(fs.readFileSync(path.join(root, 'standard-runtime.json'), 'utf8'));
    if (manifest.schemaVersion !== 1 || !Array.isArray(manifest.entries) || !manifest.entries.length) throw new Error('現行版の入口が定義されていません。');
    const files = new Set();
    const excluded = manifest.excludedDirectories || [];
    const legacy = new Set(manifest.legacyFiles || []);
    function visit(reference, from) {
        if (!reference || reference.startsWith('#') || reference.startsWith('data:')) return;
        if (reference.startsWith('/')) throw new Error(`移動可能な相対パスを使ってください: ${reference}`);
        const url = new URL(reference, pathToFileURL(from));
        if (url.protocol !== 'file:') throw new Error('現行版の一覧には外部URLを含められません。');
        const absolute = fileURLToPath(url);
        const real = fs.realpathSync(absolute);
        const relative = path.relative(root, real).split(path.sep).join('/');
        if (relative.startsWith('../') || path.isAbsolute(relative)) throw new Error('prototype外への参照です。');
        if (legacy.has(relative) || excluded.some(directory => relative === directory || relative.startsWith(`${directory}/`))) throw new Error(`現行版が開発履歴に依存しています: ${relative}`);
        if (files.has(relative)) return;
        if (!fs.statSync(real).isFile()) throw new Error(`ファイルではありません: ${relative}`);
        files.add(relative);
        const text = fs.readFileSync(real, 'utf8');
        const extension = path.extname(real);
        if (extension === '.html') {
            for (const match of text.matchAll(/<(?:script|link)\b[^>]*\b(?:src|href)=["']([^"']+)["'][^>]*>/gi)) visit(match[1], real);
            for (const match of text.matchAll(/\bdata-config=["']([^"']+)["']/gi)) visit(match[1], real);
            for (const match of text.matchAll(/<a\b[^>]*\bhref=["']([^"']+\.html(?:[?#][^"']*)?)["']/gi)) visit(match[1], real);
        } else if (extension === '.js') {
            for (const match of text.matchAll(/\b(?:import|export)\s+(?:[^;\n]*?\s+from\s+)?["']([^"']+)["']/g)) visit(match[1], real);
            for (const match of text.matchAll(/\bimport\(\s*["']([^"']+)["']\s*\)/g)) visit(match[1], real);
        } else if (extension === '.css') {
            for (const match of text.matchAll(/url\(\s*["']?([^"')\s]+)["']?\s*\)|@import\s+["']([^"']+)["']/g)) visit(match[1] || match[2], real);
        } else if (extension === '.json') {
            const data = JSON.parse(text);
            if (!Array.isArray(data) && data.questionFiles) {
                if (!Array.isArray(data.questionFiles)) throw new Error(`questionFilesが配列ではありません: ${relative}`);
                data.questionFiles.forEach(file => visit(file, real));
            }
        }
    }
    for (const entry of manifest.entries) visit(entry, path.join(root, 'standard-runtime.json'));
    return { entries: [...manifest.entries], files: [...files].sort() };
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
    try {
        const result = auditRuntime();
        if (process.argv.includes('--json')) console.log(JSON.stringify(result, null, 2));
        else console.log(`PASS standard runtime: ${result.entries.length} entries, ${result.files.length} files; no legacy dependencies or missing files.`);
    } catch (error) { console.error(error.message); process.exitCode = 1; }
}
