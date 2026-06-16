// AETHER Dashboard Screenshot Script
// Uses Playwright to capture all pages at 1440x900

import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:8000';
const SCREENSHOTS_DIR = 'assets/screenshots';
const VIEWPORT = { width: 1440, height: 900 };

const PAGES = [
  { route: '/',        file: 'dashboard.png',  label: 'Dashboard — Live Simulation' },
  { route: '/settings', file: 'settings.png',   label: 'Settings — Configuration Panel' },
  { route: '/scenarios',file: 'scenarios.png',  label: 'Scenarios — Anomaly Designer' },
  { route: '/agents',  file: 'agents.png',      label: 'Agents — Solara, Veridian & Hal-90' },
  { route: '/history', file: 'history.png',     label: 'History — Past Runs & Replay' },
  { route: '/mqtt',    file: 'mqtt.png',        label: 'MQTT — Message Broker Console' },
];

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: VIEWPORT, deviceScaleFactor: 1 });
  const page = await context.newPage();

  for (const { route, file, label } of PAGES) {
    console.log(`Capturing ${route} -> ${file}`);
    try {
      await page.goto(`${BASE_URL}${route}`, { waitUntil: 'load', timeout: 30000 });
      await sleep(3000); // let HTMX/Alpine settle
      await page.screenshot({ path: `${SCREENSHOTS_DIR}/${file}`, fullPage: true });
      console.log(`  OK ${label}`);
    } catch (err) {
      console.error(`  FAIL ${err.message}`);
    }
  }

  // Dashboard with live simulation data
  console.log(`Capturing / with sim -> dashboard-sim.png`);
  try {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'load', timeout: 30000 });
    await sleep(1500);
    const btn = await page.locator('button', { hasText: /Run Simulation/i });
    if (await btn.count() > 0) {
      await btn.click();
      console.log('  Clicked Run Simulation, waiting...');
      await sleep(12000);
    }
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/dashboard-sim.png`, fullPage: true });
    console.log('  OK Dashboard with simulation data');
  } catch (err) {
    console.error(`  FAIL dashboard-sim: ${err.message}`);
  }

  await browser.close();
  console.log('\nAll screenshots captured!');
}

run().catch(err => { console.error('Fatal:', err); process.exit(1); });
