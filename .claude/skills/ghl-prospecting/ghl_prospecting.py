#!/usr/bin/env python3
"""
GHL Prospecting Automation

Automates prospect research and imports enriched leads into GoHighLevel CRM.
Uses Surfe API for email enrichment and GHL API for contact import.
Follows directive: directives/automated_prospecting_ghl_crm.md
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict

# Add _shared to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "_shared"))

try:
    import requests
except ImportError:
    print("❌ Error: requests library not installed")
    print("   Install with: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from error_reporter import report_error, report_success, report_warning
from resilience import retry


@retry(max_attempts=2)
def search_icp_companies(industry: str, max_employees: int, country: str) -> List[Dict]:
    """
    Search for companies matching ICP criteria.
    
    Note: This requires company search API (e.g., Apollo, ZoomInfo, etc.)
    Placeholder implementation.
    """
    # TODO: Integrate with company search API
    report_warning(
        "ghl-prospecting",
        f"Company search API not integrated - using placeholder for {industry}"
    )
    
    # Mock company data
    return [
        {
            "company_name": "Acme Corp",
            "domain": "acmecorp.com",
            "industry": industry,
            "employees": 50,
            "country": country
        },
        {
            "company_name": "TechStart Inc",
            "domain": "techstart.io",
            "industry": industry,
            "employees": 25,
            "country": country
        }
    ]


@retry(max_attempts=2)
def find_decision_makers(company_domain: str) -> List[Dict]:
    """
    Find decision makers at a company.
    
    Note: Requires people search API.
    Placeholder implementation.
    """
    # TODO: Integrate with people search API (Apollo, LinkedIn Sales Navigator, etc.)
    
    # Mock decision maker data
    return [
        {
            "first_name": "John",
            "last_name": "Smith",
            "title": "VP of Marketing",
            "linkedin_url": f"https://linkedin.com/in/johnsmith",
            "company": company_domain
        }
    ]


@retry(max_attempts=3, backoff_factor=3)
def enrich_with_surfe(contacts: List[Dict], surfe_api_key: str) -> List[Dict]:
    """
    Enrich contacts with email addresses via Surfe API.
    
    Args:
        contacts: List of contacts with name, company, linkedin_url
        surfe_api_key: Surfe API key
    
    Returns:
        Enriched contacts with email addresses
    """
    url = "https://api.surfe.com/v1/enrich/bulk"
    
    headers = {
        "Authorization": f"Bearer {surfe_api_key}",
        "Content-Type": "application/json"
    }
    
    # Format payload for Surfe
    payload = {
        "contacts": [
            {
                "first_name": c["first_name"],
                "last_name": c["last_name"],
                "company_domain": c["company"],
                "linkedin_url": c.get("linkedin_url")
            }
            for c in contacts
        ]
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    
    enrichment_id = response.json()["enrichment_id"]
    print(f"   Enrichment started: {enrichment_id}")
    
    # Poll for completion
    status_url = f"https://api.surfe.com/v1/enrich/status/{enrichment_id}"
    max_polls = 20
    
    for _ in range(max_polls):
        time.sleep(3)  # Wait 3 seconds between polls
        
        status_response = requests.get(status_url, headers=headers, timeout=10)
        status_response.raise_for_status()
        
        status_data = status_response.json()
        
        if status_data["status"] == "completed":
            print(f"   ✅ Enrichment complete")
            return status_data["enriched_contacts"]
        elif status_data["status"] == "failed":
            raise Exception(f"Enrichment failed: {status_data.get('error')}")
    
    raise Exception("Enrichment timeout - took too long")


@retry(max_attempts=3)
def import_to_ghl(contact: Dict, ghl_api_key: str) -> Dict:
    """
    Import contact to GoHighLevel CRM.
    
    Args:
        contact: Contact data with email, name, company, etc.
        ghl_api_key: GHL API key
    
    Returns:
        GHL contact response
    """
    url = "https://rest.gohighlevel.com/v1/contacts"
    
    headers = {
        "Authorization": f"Bearer {ghl_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "firstName": contact["first_name"],
        "lastName": contact["last_name"],
        "email": contact.get("email"),
        "companyName": contact.get("company"),
        "tags": ["prospecting", "surfe_enriched"],
        "source": "automated_prospecting",
        "customFields": {
            "title": contact.get("title"),
            "linkedin_url": contact.get("linkedin_url")
        }
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=15)
    response.raise_for_status()
    
    return response.json()


def save_results(enriched_contacts: List[Dict], output_path: Path) -> None:
    """Save enriched prospect list"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(enriched_contacts, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Automate prospecting and import to GoHighLevel CRM"
    )
    parser.add_argument("--industry", required=True, help="Target industry")
    parser.add_argument("--max-employees", type=int, default=500, help="Max employee count")
    parser.add_argument("--country", default="US", help="Country code (Alpha-2)")
    parser.add_argument("--output", default=".tmp/prospecting/enriched_leads.json", help="Output file")
    
    args = parser.parse_args()
    
    # Check API keys
    surfe_key = os.getenv("SURFE_API_KEY")
    ghl_key = os.getenv("GHL_API_KEY")
    
    if not surfe_key:
        print("❌ Error: SURFE_API_KEY not configured")
        sys.exit(1)
    
    if not ghl_key:
        print("⚠️  Warning: GHL_API_KEY not configured")
        print("   Contacts will not be imported to GHL")
    
    try:
        print(f"🔍 Searching for companies...")
        print(f"   Industry: {args.industry}")
        print(f"   Max employees: {args.max_employees}")
        print(f"   Country: {args.country}")
        
        # Search for companies
        companies = search_icp_companies(args.industry, args.max_employees, args.country)
        print(f"\n   Found {len(companies)} companies")
        
        # Find decision makers
        all_contacts = []
        for company in companies:
            print(f"\n👥 Finding decision makers at {company['company_name']}...")
            contacts = find_decision_makers(company["domain"])
            all_contacts.extend(contacts)
        
        print(f"\n   Total contacts: {len(all_contacts)}")
        
        # Enrich with Surfe
        if all_contacts:
            print(f"\n📧 Enriching contacts with Surfe...")
            enriched = enrich_with_surfe(all_contacts, surfe_key)
            print(f"   Enriched {len(enriched)} contacts with emails")
        else:
            enriched = []
        
        # Import to GHL
        imported_count = 0
        if ghl_key and enriched:
            print(f"\n📥 Importing to GoHighLevel...")
            for contact in enriched:
                if contact.get("email"):
                    try:
                        import_to_ghl(contact, ghl_key)
                        imported_count += 1
                        print(f"   ✅ {contact['first_name']} {contact['last_name']}")
                    except Exception as e:
                        report_error("ghl-prospecting", e, {"contact": contact})
        
        # Save results
        output_path = Path(args.output)
        save_results(enriched, output_path)
        
        # Report success
        report_success(
            "ghl-prospecting",
            f"Prospecting complete: {len(enriched)} enriched contacts",
            {
                "industry": args.industry,
                "companies_found": len(companies),
                "contacts_found": len(all_contacts),
                "enriched": len(enriched),
                "imported_to_ghl": imported_count,
                "output_file": str(output_path)
            }
        )
        
        print(f"\n✅ Complete!")
        print(f"   Companies: {len(companies)}")
        print(f"   Contacts: {len(all_contacts)}")
        print(f"   Enriched: {len(enriched)}")
        print(f"   Imported to GHL: {imported_count}")
        
    except Exception as e:
        report_error("ghl-prospecting", e, {"industry": args.industry})
        sys.exit(1)


if __name__ == "__main__":
    main()
