import { mkdirSync, copyFileSync, cpSync, existsSync, rmSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execSync } from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');
const distDir = path.join(rootDir, 'dist-package');

if (existsSync(distDir)) {
  rmSync(distDir, { recursive: true, force: true });
}

mkdirSync(path.join(distDir, 'frontend'), { recursive: true });
mkdirSync(path.join(distDir, 'backend'), { recursive: true });
mkdirSync(path.join(distDir, 'n8n'), { recursive: true });

console.log('Building frontend...');
execSync('npm run build', { cwd: rootDir, stdio: 'inherit', shell: true });

cpSync(path.join(rootDir, 'frontend', 'dist'), path.join(distDir, 'frontend', 'dist'), { recursive: true });
cpSync(path.join(rootDir, 'frontend', 'package.json'), path.join(distDir, 'frontend', 'package.json'));
cpSync(path.join(rootDir, 'frontend', 'vite.config.js'), path.join(distDir, 'frontend', 'vite.config.js'));
cpSync(path.join(rootDir, 'frontend', 'index.html'), path.join(distDir, 'frontend', 'index.html'));
cpSync(path.join(rootDir, 'frontend', 'postcss.config.js'), path.join(distDir, 'frontend', 'postcss.config.js'));
cpSync(path.join(rootDir, 'frontend', 'tailwind.config.js'), path.join(distDir, 'frontend', 'tailwind.config.js'));
cpSync(path.join(rootDir, 'frontend', 'src'), path.join(distDir, 'frontend', 'src'), { recursive: true });

cpSync(path.join(rootDir, 'backend'), path.join(distDir, 'backend'), { recursive: true });
cpSync(path.join(rootDir, 'n8n'), path.join(distDir, 'n8n'), { recursive: true });
cpSync(path.join(rootDir, 'README.md'), path.join(distDir, 'README.md'));

console.log(`Distribution package created at ${distDir}`);
