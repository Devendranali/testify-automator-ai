# utils/prompt_utils.py

from typing import List


# ============================================================
# MASTER PROMPT — Generates:
# 1. Positive UI test
# 2. Negative UI test
# 3. Edge UI test
# 4. Accessibility test
# 5. Security test
# ============================================================

def build_prompt(
    story_block: str,
    method_map: dict,
    page_names: list[str],
    site_url: str,
    dynamic_steps: list[str]
) -> str:

    # Format POM methods grouped by page
    page_method_section = "\n".join(
        f"# {p}:\n" + "\n".join(f"- def {m}" for m in method_map.get(p, []))
        for p in page_names
    )

    dynamic_steps_joined = "\n".join(dynamic_steps)

    return f"""
You are a **Senior Automation Architect**. Generate **Playwright Python test scripts** for the following user story:

USER STORY:
{story_block}


===========================================
🚨 ABSOLUTE RULES (MUST FOLLOW)
===========================================

1. **USE ONLY the POM methods listed below.**
   - NEVER create or guess new method names.
   - NEVER write locators: no page.locator(), no CSS, no XPath.
   - ONLY call existing POM functions: def method(page, ...).

2. **DO NOT write import statements.**
   The runner auto-handles imports.

3. **DO NOT create helper functions.**
   Only write test functions.

4. **EVERY test MUST start with:**
       page.goto("{site_url}")

5. **If a step from the story is missing a POM method:**
       Write inside the test:
       # Skipped step due to missing method: <step>

6. **Output ONLY valid Python code — no markdown, no comments outside the test body.**


===========================================
📌 REQUIRED TEST FUNCTIONS
===========================================

You MUST generate the following test functions:

-----------------------------------------------------------
1️⃣ **POSITIVE TEST**
Function name:
    test_positive_feature()

Rules:
– Follow the correct flow exactly as per the user story  
– Use valid inputs  
– Use POM methods in correct order  
– Use assert_* POM methods wherever available  

-----------------------------------------------------------
2️⃣ **NEGATIVE TEST**
Function name:
    test_negative_feature()

Rules:
– Use invalid/missing inputs  
– Example: empty strings, wrong formats  
– Should lead to failure paths  
– Use assert_* methods where applicable  

-----------------------------------------------------------
3️⃣ **EDGE TEST**
Function name:
    test_edge_feature()

Rules:
– Use extreme inputs:
    "A" * 256
    "!@#$%^&*()"
    very long email
– Still follow user story steps  
– Use POM methods only  

-----------------------------------------------------------
4️⃣ **ACCESSIBILITY TEST**
Function name:
    test_accessibility_feature()

Rules:
– Follow positive flow navigation using ONLY POM methods  
– At logical checkpoints validate accessibility using Playwright:

        expect(page.get_by_text("Full Name")).to_be_visible()

– DO NOT create or use accessibility helper methods  
– DO NOT use Axe directly (your framework triggers it automatically)  

-----------------------------------------------------------
5️⃣ **SECURITY TESTS**

You MUST generate the following security test functions:

**A) XSS (Cross-Site Scripting) TEST**
Function name:
    test_security_xss()

Rules:
– Inject XSS payloads into **every input POM method**.
      Payload 1: "<script>alert('XSS')</script>"
      Payload 2: '"><img src=x onerror=alert("XSS")>'
– Use a different payload for each input field if possible.
– After submitting, assert that the script was not executed or rendered:
      assert "<script>" not in page.content()
– Use only POM methods for navigation & input.

**B) SQL Injection (SQLi) TEST**
Function name:
    test_security_sqli()

Rules:
– Inject SQLi payloads into **every input POM method**.
      Payload 1: "' OR '1'='1"
      Payload 2: "' OR '1'='1' --"
– Use a different payload for each input field if possible.
– After submitting, check for generic error pages or unexpected success.
– Use only POM methods for navigation & input.

**C) SECURITY HEADERS TEST**
Function name:
    test_security_headers()

Rules:
– Navigate to the site's main URL.
– Verify that essential security headers are present.
      response = page.goto("{site_url}")
      headers = response.headers
      assert "content-security-policy" in headers
      assert "x-frame-options" in headers  


===========================================
📄 PAGE OBJECT METHODS (ALLOWED)
===========================================
{page_method_section}


===========================================
💡 EXTRA HINTS
===========================================
{dynamic_steps_joined}


===========================================
🎯 OUTPUT FORMAT — CRITICAL
===========================================

Output ONLY valid Python test functions:

❌ No imports  
❌ No markdown  
❌ No helper functions  
❌ No text outside the tests  

Each test MUST follow:

def test_positive_feature(page):
    page.goto("SITE_URL")
    <POM method calls>
    <assertions>

NOW GENERATE ALL FIVE TEST FUNCTIONS.
"""


# ============================================================
# SECURITY-ONLY PROMPT
# ============================================================
def build_security_prompt(
    story_block: str,
    method_map: dict,
    page_names: list[str],
    site_url: str,
) -> str:

    page_method_section = "\n".join(
        f"# {p}:\n" + "\n".join(f"- def {m}" for m in method_map.get(p, []))
        for p in page_names
    )

    input_methods = []
    for page, methods in method_map.items():
        for method in methods:
            if method.startswith(("enter_", "fill_")):
                input_methods.append(f"{method}()  # page: {page}")

    payload_list = "\n".join(f"- {m}" for m in input_methods)

    return f"""
You are a **Senior Security Automation Architect** working on an enterprise AI-driven testing platform called **Testify**.

Your task is to generate **Playwright Python security test cases** using **ONLY Page Object Model methods**.

====================================================
ABSOLUTE RULES (MUST FOLLOW – NO EXCEPTIONS)
====================================================

1. USE ONLY the provided Page Object Model methods.
   - NEVER use locators, selectors, page.locator, get_by_*, or raw Playwright actions.
2. DO NOT pass `page` as an argument to page methods.
3. ENABLE SmartAI self-healing at the start of every test:
       patch_page_with_smartai(page)
4. DO NOT add imports, helper functions, comments, or explanations.
5. DO NOT assert input field values after entering security payloads.
6. OUTPUT ONLY executable Python test functions.
7. Use pytest style functions with signature: def test_*(page):

====================================================
USER STORY
====================================================
{story_block}

====================================================
AVAILABLE PAGE METHODS
====================================================
{page_method_section}

====================================================
INPUT FIELDS IDENTIFIED (FOR PAYLOAD INJECTION)
====================================================
{payload_list}

====================================================
XSS (CROSS-SITE SCRIPTING) TEST
====================================================

Function name: test_security_xss(page)

MANDATORY RULES:
1. Navigate through the application using ONLY page methods.
2. Inject the following payloads into EVERY input field:
   - "<script>alert('XSS')</script>"
   - '"><img src=x onerror=alert("XSS")>'
3. BEFORE submitting the form, register a dialog listener:
       dialogs = []
       page.on("dialog", lambda d: dialogs.append(d.message))
4. Submit the form using POM methods.
5. ASSERT that NO JavaScript dialog was triggered:
       assert not dialogs
6. DO NOT use page.content() or page.inner_text() to detect XSS.

====================================================
SQL INJECTION (SQLi) TEST
====================================================

Function name: test_security_sqli(page)

MANDATORY RULES:
1. Navigate using ONLY POM methods.
2. Inject the following payloads into EVERY input field:
   - "' OR '1'='1"
   - "' OR '1'='1' --"
3. Submit the form using POM methods.
4. ASSERT that the page does NOT contain SQL error indicators:
       "sql", "syntax", "exception", "database"
5. Do NOT assume backend behavior — only validate absence of errors.

====================================================
SECURITY HEADERS TEST
====================================================

Function name: test_security_headers(page)

MANDATORY RULES:
1. Navigate directly to the application URL:
       response = page.goto("{site_url}")
2. Read headers from the response object.
3. ASSERT presence of the following headers:
       - content-security-policy
       - x-frame-options
       - x-content-type-options
       - strict-transport-security

====================================================
FINAL OUTPUT REQUIREMENTS
====================================================

- Generate EXACTLY these three functions:
    - test_security_xss(page)
    - test_security_sqli(page)
    - test_security_headers(page)
- Do NOT generate anything else.
- Do NOT wrap output in markdown.
- Do NOT explain.

GENERATE THE CODE NOW.
"""

# ============================================================
# ACCESSIBILITY-ONLY PROMPT
# ============================================================

def build_accessibility_prompt(
    story_block: str,
    method_map: dict,
    page_names: list[str],
    site_url: str,
) -> str:

    page_method_section = "\n".join(
        f"# {p}:\n" + "\n".join(f"- def {m}" for m in method_map.get(p, []))
        for p in page_names
    )

    return f"""
You are an **Accessibility Testing Specialist**.  
Generate ONE test function named: `test_accessibility(page)`.

USER STORY:
{story_block}

Allowed Page Methods:
{page_method_section}

=========================
ACCESSIBILITY RULES
=========================

1. Navigate only using POM methods.
2. Follow the same flow as the positive UI journey.
3. At each page-level checkpoint include accessibility validation like:

       expect(page.get_by_text("Full Name")).to_be_visible()

4. DO NOT:
   – Use Axe directly
   – Invent accessibility helper methods
   – Create imports
   – Create helper functions

5. Output ONLY valid Python code.

Generate the test now.
"""
