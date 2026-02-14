#!/usr/bin/env python3
"""
Dream 100 Automation - Main Orchestrator
Executes the complete D100 workflow for healthcare practice outreach
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add modules directory to path
sys.path.insert(0, str(Path(__file__).parent / "modules"))

from d100_scraper import D100Scraper
from d100_brightlocal_keywords import D100BrightLocalKeywords
from d100_seo_audit import D100SEOAudit
from d100_app_builder import D100AppBuilder
from d100_ads_builder import D100AdsBuilder
from d100_email_builder import D100EmailBuilder


class D100Orchestrator:
    """Main workflow orchestrator for Dream 100 automation"""

    def __init__(self, website_url, booking_url, context=None, semrush_screenshot=None, semrush_csv=None):
        self.website_url = website_url
        self.booking_url = booking_url
        self.context = context or ""
        self.semrush_screenshot = semrush_screenshot
        self.semrush_csv = semrush_csv

        # Create timestamped run directory
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = Path(__file__).parent / "output" / "d100_runs" / self.timestamp
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # Initialize modules
        self.scraper = D100Scraper(self.run_dir)
        self.brightlocal = D100BrightLocalKeywords(self.run_dir)
        self.seo_audit = D100SEOAudit(self.run_dir)
        self.app_builder = D100AppBuilder(self.run_dir)
        self.ads_builder = D100AdsBuilder(self.run_dir)
        self.email_builder = D100EmailBuilder(self.run_dir)

        # Store inputs
        self._save_inputs()

    def _save_inputs(self):
        """Save user inputs to JSON"""
        inputs = {
            "website_url": self.website_url,
            "booking_url": self.booking_url,
            "context": self.context,
            "semrush_screenshot": self.semrush_screenshot,
            "semrush_csv": self.semrush_csv,
            "timestamp": self.timestamp,
            "run_id": self.timestamp
        }

        with open(self.run_dir / "inputs.json", "w") as f:
            json.dump(inputs, f, indent=2)

    def _print_banner(self, message):
        """Print formatted banner"""
        line = "═" * 63
        print(f"\n{line}")
        print(f"{message}")
        print(f"{line}\n")

    def run(self):
        """Execute complete D100 workflow"""

        self._print_banner("🚀 DREAM 100 AUTOMATION - STARTING")

        print(f"📍 Website: {self.website_url}")
        print(f"📅 Run ID: {self.timestamp}")
        print(f"💾 Output: {self.run_dir}\n")

        # PHASE 1: Website Scraping
        self._print_banner("PHASE 1: WEBSITE SCRAPING")

        print("🔍 Scraping website with Perplexity Sonar...")
        scrape_result = self.scraper.scrape(self.website_url, self.context)

        if not scrape_result["success"]:
            print(f"❌ Scrape failed: {scrape_result['error']}")
            return False

        print(f"✅ Website scraped ({scrape_result['pages_crawled']} pages)")

        print("\n🔄 Converting to structured JSON with Claude Sonnet...")
        json_result = self.scraper.convert_to_json(scrape_result["raw_markdown"])

        if not json_result["success"]:
            print(f"❌ JSON conversion failed: {json_result['error']}")
            return False

        print(f"✅ Structured JSON generated")

        # Load structured data
        with open(json_result["json_path"]) as f:
            structured_data = json.load(f)

        # PHASE 1.5: Generate BrightLocal Keywords & Send to Slack
        self._print_banner("PHASE 1.5: BRIGHTLOCAL KEYWORDS")

        print("📊 Generating 100 local SEO keywords...")
        brightlocal_result = self.brightlocal.generate(structured_data)

        if brightlocal_result["success"]:
            print(f"✅ {brightlocal_result['total_keywords']} keywords generated")
            print(f"💾 Saved to: {brightlocal_result['keywords_path']}")
            if brightlocal_result.get("slack_sent"):
                print(f"📢 Sent to Slack!")
            else:
                print(f"⚠️  Slack notification skipped (no webhook)")
        else:
            print(f"⚠️  BrightLocal keyword generation failed: {brightlocal_result['error']}")

        # PHASE 2: SEO Analysis (if screenshot + CSV provided)
        seo_data = None
        if self.semrush_screenshot and self.semrush_csv:
            self._print_banner("PHASE 2: SEO ANALYSIS FOR DOCTORS")

            print("📈 Analyzing SEMrush data with Claude Sonnet 3.7...")
            print(f"   Screenshot: {self.semrush_screenshot}")
            print(f"   Keywords CSV: {self.semrush_csv}")

            seo_result = self.seo_audit.analyze(
                self.semrush_screenshot,
                self.semrush_csv,
                structured_data
            )

            if seo_result["success"]:
                print(f"✅ Doctor-friendly SEO analysis generated")
                print(f"💾 Saved to: {seo_result['analysis_path']}")
                seo_data = seo_result
            else:
                print(f"⚠️  SEO analysis failed: {seo_result['error']}")
        elif self.semrush_screenshot or self.semrush_csv:
            print("\n⚠️  Skipping SEO analysis: Need BOTH screenshot AND CSV")
            print("   Provided: ", end="")
            if self.semrush_screenshot:
                print("Screenshot ✓ ", end="")
            if self.semrush_csv:
                print("CSV ✓", end="")
            print()
        else:
            print("\n⏭️  Skipping SEO analysis (no SEMrush CSV provided)")

        # PHASE 3: Parallel Asset Generation
        self._print_banner("PHASE 3: GENERATING ASSETS (PARALLEL)")

        results = {
            "scrape": scrape_result,
            "json": json_result,
            "seo": seo_data,
            "app": None,
            "ads": None,
            "emails": None
        }

        # Build health assessment app
        print("🏥 Building health assessment app...")
        app_result = self.app_builder.build(
            structured_data,
            self.booking_url
        )

        if app_result["success"]:
            print(f"✅ Health app generated ({app_result['file_size_kb']} KB)")
            print(f"💾 {app_result['html_path']}")
            results["app"] = app_result
        else:
            print(f"❌ App generation failed: {app_result['error']}")

        # Build Google Ads campaigns
        print("\n📢 Building Google Ads campaigns...")
        ads_result = self.ads_builder.build(
            structured_data,
            seo_data
        )

        if ads_result["success"]:
            print(f"✅ Google Ads generated ({ads_result['campaigns_generated']} campaigns)")
            print(f"💾 {ads_result['main_file']}")
            results["ads"] = ads_result
        else:
            print(f"❌ Ads generation failed: {ads_result['error']}")

        # Build email sequence
        print("\n📧 Building email sequence...")
        email_result = self.email_builder.build(
            structured_data,
            self.booking_url
        )

        if email_result["success"]:
            print(f"✅ Email sequence generated ({email_result['emails_generated']} emails)")
            print(f"💾 {email_result['main_file']}")
            results["emails"] = email_result
        else:
            print(f"❌ Email generation failed: {email_result['error']}")

        # PHASE 4: Compile outputs
        self._print_banner("PHASE 4: COMPILATION")

        manifest = self._create_manifest(results)

        manifest_path = self.run_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        print(f"✅ Manifest created: {manifest_path}")

        # Final summary
        self._print_banner("✅ DREAM 100 AUTOMATION - COMPLETE")

        print(f"📁 Output Directory: {self.run_dir}\n")

        print("📦 ASSETS GENERATED:")
        if results["app"]:
            print(f"  ✅ Health Assessment App")
        if results["ads"]:
            print(f"  ✅ Google Ads Campaigns (3)")
        if results["emails"]:
            print(f"  ✅ Email Sequence (3 emails)")
        if results["seo"]:
            print(f"  ✅ SEO Intelligence Report")

        print(f"\n💰 Estimated API Cost: ${manifest['estimated_cost']:.2f}")
        print(f"⏱️  Total Time: {manifest['total_time_seconds']}s\n")

        return True

    def _create_manifest(self, results):
        """Create final manifest of all outputs"""
        return {
            "run_id": self.timestamp,
            "website_url": self.website_url,
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "outputs": {
                "scrape_data": {
                    "raw_markdown": str(results["json"]["raw_path"]) if results["json"] else None,
                    "structured_json": str(results["json"]["json_path"]) if results["json"] else None,
                },
                "seo_data": {
                    "keywords": str(results["seo"]["keywords_path"]) if results.get("seo") else None,
                    "insights": str(results["seo"]["output_path"]) if results.get("seo") else None,
                } if results.get("seo") else None,
                "health_app": str(results["app"]["html_path"]) if results.get("app") else None,
                "google_ads": str(results["ads"]["main_file"]) if results.get("ads") else None,
                "email_sequence": str(results["emails"]["main_file"]) if results.get("emails") else None,
            },
            "estimated_cost": 0.89,  # Updated cost estimate
            "total_time_seconds": 0,  # TODO: Track actual time
        }


def main():
    parser = argparse.ArgumentParser(description="Dream 100 Automation")
    parser.add_argument("--url", required=True, help="Target website URL")
    parser.add_argument("--booking", required=True, help="Booking URL or phone number")
    parser.add_argument("--context", help="Optional additional context")
    parser.add_argument("--semrush-screenshot", help="Path to SEMrush site overview screenshot (PNG/JPG)")
    parser.add_argument("--semrush-csv", help="Path to SEMrush keyword rankings CSV export")

    args = parser.parse_args()

    # Create orchestrator
    orchestrator = D100Orchestrator(
        website_url=args.url,
        booking_url=args.booking,
        context=args.context,
        semrush_screenshot=args.semrush_screenshot,
        semrush_csv=args.semrush_csv
    )

    # Run automation
    success = orchestrator.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
