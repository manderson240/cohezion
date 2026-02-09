const { firefox } = require('playwright');
const path = require('path');

(async () => {
    const browser = await firefox.launch();
    const page = await browser.newPage();

    // Navigate to the local dev server (assuming it's running on 5173 or similar)
    // For this verification, we'll try to open the index.html directly if possible or
    // just assume the user will run it.
    // As a safer bet for "local verification", I'll just capture the "state" of the files.
    // Actually, I can use the browser tool to verify if I can't run playwright headlessly here easily.
    // But the instructions said "use our local playwright version".

    try {
        await page.goto('http://localhost:5173');
        await page.screenshot({ path: '/home/mike-anderson/.gemini/antigravity/brain/2affbcca-b8be-4a9f-a143-509531a03543/portal_verify.png' });
        console.log('Screenshot captured.');
    } catch (e) {
        console.log('Dev server not reachable. Verification requires the dev server to be running.');
    }

    await browser.close();
})();
