import puppeteer from "puppeteer";
import { pathToFileURL } from "node:url";

const browser = await puppeteer.launch({ headless: true });
try {
  const page = await browser.newPage();
  await page.goto(pathToFileURL(process.argv[2]).href);
  await page.evaluate(() => document.fonts.ready);
  const result = await page.evaluate(() => {
    const svg = document.documentElement;
    svg.style.width = `${svg.viewBox.baseVal.width}px`;
    svg.style.maxWidth = "none";
    const box = svg.getBoundingClientRect();
    const labels = [...document.querySelectorAll(".node text")].map((element) => {
      const range = document.createRange();
      range.selectNodeContents(element);
      const text = range.getBoundingClientRect();
      return {
        text: element.textContent,
        left: text.left,
        right: text.right,
        top: text.top,
        bottom: text.bottom,
        clipped:
          text.left < box.left - 1 ||
          text.right > box.right + 1 ||
          text.top < box.top - 1 ||
          text.bottom > box.bottom + 1,
      };
    });
    const overlaps = labels.filter((a, i) =>
      labels.slice(i + 1).some((b) =>
        Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 &&
        Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1,
      ),
    );
    return {
      labels: labels.map((label) => label.text),
      clipped: labels.filter((label) => label.clipped).map((label) => label.text),
      overlaps: overlaps.map((label) => label.text),
    };
  });
  console.log(JSON.stringify(result));
} finally {
  await browser.close();
}
