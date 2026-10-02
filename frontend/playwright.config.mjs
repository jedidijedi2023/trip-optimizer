import {defineConfig,devices} from '@playwright/test';

export default defineConfig({
 testDir:'./tests/e2e',
 timeout:30000,
 workers:1,
 use:{...devices['Desktop Chrome'],baseURL:process.env.TRIP_BASE_URL||'http://127.0.0.1:4173/trip-optimizer/',trace:'retain-on-failure'},
});
