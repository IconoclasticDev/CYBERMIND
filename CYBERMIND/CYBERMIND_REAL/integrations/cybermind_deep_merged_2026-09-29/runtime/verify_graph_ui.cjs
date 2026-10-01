const { chromium } = require('C:/Users/as030/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const port = process.env.CYBERMIND_TEST_PORT;
  const demo = process.env.CYBERMIND_DEMO_PCAP;
  const output = path.join(__dirname, 'graph_ui_verification');
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: 'Upload PCAP / CSV' }).click();
  await page.locator('input[type=file][accept*="pcap"]').setInputFiles(demo);
  await page.getByRole('button', { name: 'Ingest & Run World Model' }).click();
  await page.getByText('Network Flows Ingested Successfully!').waitFor({ timeout: 120000 });
  await page.getByRole('button', { name: 'View Live Graph' }).click();
  await page.getByText('Showing 12 of', { exact: false }).waitFor({ timeout: 30000 });
  const topology = page.getByRole('img', { name: 'Network topology' });
  const before = {
    summary: await page.getByText('Showing 12 of', { exact: false }).first().textContent(),
    nodes: await topology.locator('g.cursor-pointer.group').count(),
    paths: await topology.locator('path').count(),
  };
  await topology.screenshot({ path: path.join(output, 'pcap_graph.png') });
  await topology.locator('g.cursor-pointer.group').first().click();
  before.nodePanelOpened = await page.getByText('Node Intelligence', { exact: false }).count() > 0 ||
    await page.getByText('Host Intelligence', { exact: false }).count() > 0;
  if (await page.getByRole('dialog', { name: /^Node detail/ }).count()) {
    before.nodePanelOpened = true;
    await page.getByRole('dialog', { name: /^Node detail/ }).getByRole('button', { name: 'Close' }).first().click();
  }
  await page.getByRole('button', { name: 'Snapshot' }).click();
  before.snapshotSelected = await page.getByRole('button', { name: 'Snapshot' }).getAttribute('class');
  await page.getByRole('button', { name: 'Live', exact: true }).click();
  const summaryBeforeRepeat = await page.getByText('Showing 12 of', { exact: false }).first().textContent();
  await page.getByRole('button', { name: 'Upload PCAP / CSV' }).click();
  await page.locator('input[type=file][accept*="pcap"]').setInputFiles(demo);
  await page.getByRole('button', { name: 'Ingest & Run World Model' }).click();
  await page.getByText('Network Flows Ingested Successfully!').waitFor({ timeout: 120000 });
  before.uploadSuccess = true;
  before.summaryDuringModal = await page.getByText('Showing 12 of', { exact: false }).first().textContent();
  before.backgroundStableDuringUpload = before.summaryDuringModal === summaryBeforeRepeat;
  await page.getByRole('button', { name: 'View Live Graph' }).click();
  await page.getByText('Showing 12 of', { exact: false }).waitFor({ timeout: 30000 });
  before.summaryAfterUpload = await page.getByText('Showing 12 of', { exact: false }).first().textContent();
  before.errors = errors;
  fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify(before, null, 2));
  console.log(JSON.stringify(before, null, 2));
  await browser.close();
})().catch(error => { console.error(error); process.exitCode = 1; });
