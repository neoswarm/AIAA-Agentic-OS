#!/usr/bin/env python3
"""
AIAA Skill Structural Validator
Validates all skills have required files and proper structure.

Usage:
    python3 .claude/skills/_shared/skill_validator.py
    python3 .claude/skills/_shared/skill_validator.py --json  # JSON output only
    python3 .claude/skills/_shared/skill_validator.py --fix   # Auto-fix issues
"""
import os
import sys
import json
import re
import ast
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class SkillValidator:
    """Validates skill structure and files."""
    
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.results = []
    
    def validate_all_skills(self) -> Dict:
        """
        Validate all skills in the skills directory.
        
        Returns:
            {
                "total": 133,
                "valid": 126,
                "warnings": 5,
                "errors": 2,
                "timestamp": "2026-02-18T10:30:00Z",
                "results": [...]
            }
        """
        total = 0
        valid = 0
        warnings_count = 0
        errors_count = 0
        
        for skill_dir in sorted(self.skills_dir.iterdir()):
            # Skip non-directories and special directories
            if not skill_dir.is_dir() or skill_dir.name.startswith('_'):
                continue
            
            total += 1
            result = self.validate_skill(skill_dir)
            self.results.append(result)
            
            if result["status"] == "valid":
                valid += 1
            
            warnings_count += len([i for i in result["issues"] if i["severity"] == "warning"])
            errors_count += len([i for i in result["issues"] if i["severity"] == "error"])
        
        return {
            "total": total,
            "valid": valid,
            "warnings": warnings_count,
            "errors": errors_count,
            "timestamp": datetime.utcnow().isoformat(),
            "results": self.results
        }
    
    def validate_skill(self, skill_dir: Path) -> Dict:
        """
        Validate a single skill.
        
        Returns:
            {
                "skill": "cold-email-campaign",
                "status": "valid" | "warning" | "error",
                "has_skill_md": True,
                "has_script": True,
                "script_name": "write_cold_emails.py",
                "has_argparse": True,
                "has_help": True,
                "has_main_block": True,
                "imports_error_reporter": False,
                "has_shebang": True,
                "has_frontmatter": True,
                "no_hardcoded_keys": True,
                "syntactically_valid": True,
                "issues": [
                    {
                        "severity": "warning",
                        "message": "Script does not import error_reporter"
                    }
                ]
            }
        """
        skill_name = skill_dir.name
        issues = []
        
        # Check 1: Has SKILL.md
        skill_md = skill_dir / "SKILL.md"
        has_skill_md = skill_md.exists()
        if not has_skill_md:
            issues.append({
                "severity": "error",
                "message": "Missing SKILL.md file"
            })
        
        # Check 2: Has Python script
        py_files = list(skill_dir.glob("*.py"))
        has_script = len(py_files) > 0
        script_name = py_files[0].name if py_files else None
        
        if not has_script:
            issues.append({
                "severity": "error",
                "message": "No Python script found"
            })
        
        # Initialize script checks
        has_argparse = False
        has_help = False
        has_main_block = False
        imports_error_reporter = False
        has_shebang = False
        no_hardcoded_keys = True
        syntactically_valid = True
        
        # If we have a script, validate it
        if py_files:
            script_file = py_files[0]
            
            try:
                script_content = script_file.read_text()
                
                # Check 3: Has shebang
                has_shebang = script_content.startswith('#!/usr/bin/env python')
                if not has_shebang:
                    issues.append({
                        "severity": "warning",
                        "message": "Script missing shebang line (#!/usr/bin/env python3)"
                    })
                
                # Check 4: Has if __name__ == "__main__" block
                has_main_block = 'if __name__ == "__main__"' in script_content
                if not has_main_block:
                    issues.append({
                        "severity": "warning",
                        "message": "Script missing if __name__ == '__main__' block"
                    })
                
                # Check 5: Has argparse or sys.argv handling
                has_argparse = 'argparse' in script_content or 'ArgumentParser' in script_content
                if not has_argparse and 'sys.argv' not in script_content:
                    issues.append({
                        "severity": "warning",
                        "message": "Script has no argument parsing (argparse or sys.argv)"
                    })
                
                # Check 6: Has --help support
                has_help = '--help' in script_content or 'add_argument' in script_content
                if has_argparse and not has_help:
                    issues.append({
                        "severity": "warning",
                        "message": "Script uses argparse but may not have --help support"
                    })
                
                # Check 7: Imports error_reporter (optional but recommended)
                imports_error_reporter = 'error_reporter' in script_content or 'from _shared import' in script_content
                if not imports_error_reporter:
                    issues.append({
                        "severity": "info",
                        "message": "Script does not import shared error_reporter utilities"
                    })
                
                # Check 8: No hardcoded API keys
                api_key_patterns = [
                    r'(api_key|API_KEY)\s*=\s*["\'][a-zA-Z0-9_-]{20,}["\']',
                    r'sk-[a-zA-Z0-9]{20,}',
                    r'Bearer\s+[a-zA-Z0-9_-]{20,}'
                ]
                
                for pattern in api_key_patterns:
                    if re.search(pattern, script_content):
                        no_hardcoded_keys = False
                        issues.append({
                            "severity": "error",
                            "message": f"Script may contain hardcoded API key (pattern: {pattern})"
                        })
                
                # Check 9: Syntactically valid Python
                try:
                    ast.parse(script_content)
                except SyntaxError as e:
                    syntactically_valid = False
                    issues.append({
                        "severity": "error",
                        "message": f"Script has syntax error: {e.msg} at line {e.lineno}"
                    })
            
            except Exception as e:
                issues.append({
                    "severity": "error",
                    "message": f"Could not read or parse script: {str(e)}"
                })
        
        # Check SKILL.md if it exists
        has_frontmatter = False
        frontmatter_complete = False
        
        if has_skill_md:
            try:
                md_content = skill_md.read_text()
                lines = md_content.split('\n')
                
                # Check 10: Has frontmatter
                if lines and lines[0] == '---':
                    has_frontmatter = True
                    
                    # Check frontmatter has required fields
                    frontmatter_text = []
                    for line in lines[1:]:
                        if line == '---':
                            break
                        frontmatter_text.append(line)
                    
                    frontmatter_str = '\n'.join(frontmatter_text)
                    has_name = 'name:' in frontmatter_str
                    has_description = 'description:' in frontmatter_str
                    
                    frontmatter_complete = has_name and has_description
                    
                    if not has_name:
                        issues.append({
                            "severity": "warning",
                            "message": "SKILL.md frontmatter missing 'name' field"
                        })
                    
                    if not has_description:
                        issues.append({
                            "severity": "warning",
                            "message": "SKILL.md frontmatter missing 'description' field"
                        })
                
                else:
                    issues.append({
                        "severity": "warning",
                        "message": "SKILL.md missing YAML frontmatter"
                    })
                
                # Check 11: SKILL.md references correct script
                if script_name and script_name not in md_content:
                    issues.append({
                        "severity": "warning",
                        "message": f"SKILL.md does not reference script '{script_name}'"
                    })
            
            except Exception as e:
                issues.append({
                    "severity": "error",
                    "message": f"Could not read SKILL.md: {str(e)}"
                })
        
        # Determine overall status
        has_errors = any(i["severity"] == "error" for i in issues)
        has_warnings = any(i["severity"] == "warning" for i in issues)
        
        if has_errors:
            status = "error"
        elif has_warnings:
            status = "warning"
        else:
            status = "valid"
        
        return {
            "skill": skill_name,
            "status": status,
            "has_skill_md": has_skill_md,
            "has_script": has_script,
            "script_name": script_name,
            "has_argparse": has_argparse,
            "has_help": has_help,
            "has_main_block": has_main_block,
            "imports_error_reporter": imports_error_reporter,
            "has_shebang": has_shebang,
            "has_frontmatter": has_frontmatter,
            "frontmatter_complete": frontmatter_complete if has_frontmatter else False,
            "no_hardcoded_keys": no_hardcoded_keys,
            "syntactically_valid": syntactically_valid,
            "issues": issues
        }
    
    def print_report(self, report: Dict):
        """Print a human-readable report to terminal."""
        print("\n" + "="*80)
        print("AIAA SKILL STRUCTURAL VALIDATION REPORT")
        print("="*80)
        print(f"\nTimestamp: {report['timestamp']}")
        print(f"Total Skills: {report['total']}")
        print(f"Valid: {report['valid']} ({report['valid']/report['total']*100:.1f}%)")
        print(f"Warnings: {report['warnings']}")
        print(f"Errors: {report['errors']}")
        print("\n" + "-"*80)
        
        # Group by status
        valid_skills = [r for r in report['results'] if r['status'] == 'valid']
        warning_skills = [r for r in report['results'] if r['status'] == 'warning']
        error_skills = [r for r in report['results'] if r['status'] == 'error']
        
        # Print errors first
        if error_skills:
            print(f"\n🔴 SKILLS WITH ERRORS ({len(error_skills)}):")
            print("-"*80)
            for result in error_skills:
                print(f"\n  {result['skill']}")
                for issue in result['issues']:
                    if issue['severity'] == 'error':
                        print(f"    ❌ {issue['message']}")
        
        # Then warnings
        if warning_skills:
            print(f"\n⚠️  SKILLS WITH WARNINGS ({len(warning_skills)}):")
            print("-"*80)
            for result in warning_skills:
                print(f"\n  {result['skill']}")
                for issue in result['issues']:
                    if issue['severity'] == 'warning':
                        print(f"    ⚠️  {issue['message']}")
        
        # Summary of valid skills
        if valid_skills:
            print(f"\n✅ VALID SKILLS ({len(valid_skills)}):")
            print("-"*80)
            # Just list names, 5 per line
            names = [r['skill'] for r in valid_skills]
            for i in range(0, len(names), 5):
                print("  " + ", ".join(names[i:i+5]))
        
        print("\n" + "="*80)
        print(f"Validation complete. Report saved to: .tmp/skill_validation_report.json")
        print("="*80 + "\n")
    
    def save_json_report(self, report: Dict, output_path: Path):
        """Save report as JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Validate AIAA skill structure and files'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output JSON only (no terminal report)'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Attempt to auto-fix issues (not yet implemented)'
    )
    parser.add_argument(
        '--skills-dir',
        type=str,
        help='Path to skills directory (default: auto-detect)'
    )
    
    args = parser.parse_args()
    
    # Find skills directory
    if args.skills_dir:
        skills_dir = Path(args.skills_dir)
    else:
        # Auto-detect from script location
        script_dir = Path(__file__).parent
        skills_dir = script_dir.parent
    
    if not skills_dir.exists():
        print(f"Error: Skills directory not found: {skills_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Run validation
    validator = SkillValidator(skills_dir)
    report = validator.validate_all_skills()
    
    # Save JSON report
    output_path = Path('.tmp/skill_validation_report.json')
    validator.save_json_report(report, output_path)
    
    # Print report unless --json flag
    if not args.json:
        validator.print_report(report)
    else:
        print(json.dumps(report, indent=2))
    
    # Exit with error code if there are errors
    if report['errors'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
