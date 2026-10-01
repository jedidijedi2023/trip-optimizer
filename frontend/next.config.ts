import type { NextConfig } from 'next';
const githubPages = process.env.GITHUB_PAGES === 'true';
const repository = process.env.GITHUB_REPOSITORY?.split('/')[1] || '';
if (githubPages && !repository) throw new Error('GITHUB_REPOSITORY is required for GitHub Pages builds');
const basePath = githubPages && !repository.endsWith('.github.io') ? `/${repository}` : '';
const config: NextConfig = {
  reactStrictMode: true,
  ...(githubPages ? {output: 'export' as const, trailingSlash: true} : {}),
  ...(basePath ? {basePath} : {}),
  env: {
    NEXT_PUBLIC_SITE_BASE_PATH: basePath,
    NEXT_PUBLIC_STATIC_DEPLOY: githubPages ? 'true' : 'false',
  },
};
export default config;
