#!/usr/bin/env python3
"""
Script pour exporter le visuel HTML en image PNG
"""

import asyncio
from pathlib import Path

async def export_visuel():
    from playwright.async_api import async_playwright
    
    html_path = Path(__file__).parent / "visuel-jeu-concours.html"
    output_path = Path(__file__).parent / "visuel-jeu-concours.png"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1200, 'height': 1200})
        
        await page.goto(f"file://{html_path.absolute()}")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(1)
        
        visual = await page.query_selector(".visual")
        
        if visual:
            await visual.screenshot(path=str(output_path), type="png")
            print(f"✅ Visuel exporté : {output_path}")
        else:
            print("❌ Élément .visual non trouvé")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(export_visuel())
