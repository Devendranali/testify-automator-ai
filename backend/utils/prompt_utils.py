# utils/prompt_utils.py
from typing import List

# def build_prompt(
#     story_block: str,
#     method_map: dict,
#     page_names: list[str],
#     site_url: str,
#     dynamic_steps: list[str]
# ) -> str:
#     page_method_section = "\n".join(
#         f"# {p}:\n" + "\n".join(f"- def {m}" for m in method_map.get(p, [])) for p in page_names
#     )
#     dynamic_steps_joined = "\n".join(dynamic_steps)

#     return (
#         f"You are a senior QA automation engineer tasked to write Playwright Python tests for the following user stories:\n"
#         f"{story_block}\n"
#         f"\n"
#         f"Rules:\n"
#         f"- For each user story, generate one **positive**, one **negative**, and one **edge case** test function. "
#         f"These must cover:\n"
#         f"  * Positive: The standard expected flow.\n"
#         f"  * Negative: A flow with invalid or missing data, expecting failure or error.\n"
#         f"  * Edge case: A boundary or unusual condition (e.g. blank, very long, special characters).\n"
#         f"- Name test functions as test_positive_<feature>, test_negative_<feature>, and test_edge_<feature>.\n"
#         f"- The tests must cover the entire end-to-end scenario for the story.\n"
#         f"- Use ONLY the functions imported from the Page Object Model (POM) files (see below). **Do NOT use any classes or class-based page objects.**\n"
#         f"- Never import or use anything from 'page_objects' or use lines like 'LoginPage(page)'.\n"
#         f"- Each test function must use the 'page' object and call the imported functions, e.g. 'fill_username(page, \"value\")'.\n"
#         f"- Do NOT define or generate any new helper functions/methods—use only those already defined.\n"
#         f"- **Do NOT generate any import statements.** (Imports will be handled automatically outside the code block.)\n"
#         f"- Do NOT use markdown, comments, or explanations—output ONLY valid Python code, starting directly with the test function(s).\n"
#         f"\n"
#         f"Site URL: {site_url}\n\n"
#         f"Page Object Methods:\n{page_method_section}\n\n"
#         f"Additional Hints:\n{dynamic_steps_joined}\n\n"
#         f"Generate the code for all three cases below."
#     )


# =========================================== MY Code ========================================
# utils/prompt_utils.py
from typing import List

# def build_prompt(
#     story_block: str,
#     method_map: dict,
#     page_names: list[str],
#     site_url: str,
#     dynamic_steps: list[str]
# ) -> str:
#     page_method_section = "\n".join(
#         f"# {p}:\n" + "\n".join(f"- def {m}" for m in method_map.get(p, [])) for p in page_names
#     )
#     dynamic_steps_joined = "\n".join(dynamic_steps)

#     return (
#         f"You are a senior QA automation engineer tasked to write Playwright Python tests for the following user stories:\n"
#         f"{story_block}\n"
#         f"\n"
#         f"Rules:\n"
#         f"- For each user story, generate one **positive**, one **negative**, and one **edge case** test function. "
#         f"These must cover:\n"
#         f"  * Positive: The standard expected flow.\n"
#         f"  * Negative: A flow with invalid or missing data, expecting failure or error.\n"
#         f"  * Edge case: A boundary or unusual condition (e.g. blank, very long, special characters).\n"
#         f"- Name test functions as test_positive_<feature>, test_negative_<feature>, and test_edge_<feature>.\n"
#         f"- The tests must cover the entire end-to-end scenario for the story.\n"
#         f"- Use ONLY the functions imported from the Page Object Model (POM) files (see below). **Do NOT use any classes or class-based page objects.**\n"
#         f"- Never import or use anything from 'page_objects' or use lines like 'LoginPage(page)'.\n"
#         f"- Each test function must use the 'page' object and call the imported functions, e.g. 'fill_username(page, \"value\")'.\n"
#         f"- Do NOT define or generate any new helper functions/methods—use only those already defined.\n"
#         f"- **Do NOT generate any import statements.** (Imports will be handled automatically outside the code block.)\n"
#         f"- Do NOT use markdown, comments, or explanations—output ONLY valid Python code, starting directly with the test function(s).\n"
#         f"\n"
#         f"Site URL: {site_url}\n\n"
#         f"Page Object Methods:\n{page_method_section}\n\n"
#         f"Additional Hints:\n{dynamic_steps_joined}\n\n"
#         f"Generate the code for all three cases below."
#     )

# original code
def build_prompt(
    story_block: str,
    method_map: dict,
    page_names: list[str],
    site_url: str,
    dynamic_steps: list[str]
) -> str:
    page_method_section = "\n".join(
        f"# {p}:\n" + "\n".join(f"- def {m}" for m in method_map.get(p, [])) for p in page_names
    )
    dynamic_steps_joined = "\n".join(dynamic_steps)

    return (
        f"You are a senior QA automation engineer tasked to write Playwright Python tests for the following user stories:\n"
        f"{story_block}\n"
        f"\n"
        f"⚠️ IMPORTANT CONSTRAINTS:\n"
        f"- ONLY use functions that are explicitly listed in the 'Page Object Methods' section below.\n"
        f"- NEVER invent, guess, or generate any method names that are not in the list.\n"
        f"- If a certain step is not supported by the listed methods, SKIP that step.\n"
        f"- Do NOT invent method names (e.g., `verify_order_success`) that are not in the list below.\n"
        f"- Go to the site URL first for each test function. \n"
        f"\n"
        f"Rules:\n"
        f"- For each user story, generate one **positive**, one **negative**, and one **edge case** test function. "
        f"These must cover:\n"
        f"  * Positive: The standard expected flow.\n"
        f"  * Negative: A flow with invalid or missing data, expecting failure or error.\n"
        f"  * Edge case: A boundary or unusual condition (e.g. blank, very long, special characters).\n"
        f"- Name test functions as test_positive_<feature>, test_negative_<feature>, and test_edge_<feature>.\n"
        f"- Inside each test function each page methods should pass 'page' as first default parameter.\n"
        f"- The tests must cover the entire end-to-end scenario for the story.\n"
        f"- Use ONLY the functions imported from the Page Object Model (POM) files (see below). **Do NOT use any classes or class-based page objects.**\n"
        f"- Never import or use anything from 'page_objects' or use lines like 'LoginPage(page)'.\n"
        f"- Each test function must use the 'page' object and call the imported functions, e.g. 'fill_username(page, \"value\")'.\n"
        f"- Do NOT define or generate any new helper functions/methods—use only those already defined.\n"
        f"- **Do NOT generate any import statements.** (Imports will be handled automatically outside the code block.)\n"
        f"- Do NOT use markdown, comments, or explanations—output ONLY valid Python code, starting directly with the test function(s).\n"
        f"\n"
        f"Site URL: {site_url}\n\n"
        f"Page Object Methods:\n{page_method_section}\n\n"
        f"Additional Hints:\n{dynamic_steps_joined}\n\n"
        f"Generate the code for all three cases below."
    )

# def build_prompt(
#     story_block: str,
#     method_map: dict,
#     page_names: list[str],
#     site_url: str,
#     dynamic_steps: list[str]
# ) -> str:
#     page_method_section = "\n".join(
#         f"# {p}:\n" + "\n".join(f"- def {m}" for m in method_map.get(p, [])) for p in page_names
#     )
#     dynamic_steps_joined = "\n".join(dynamic_steps)

#     return (
#         f"You are a senior QA automation engineer tasked to write Playwright Python tests for the following user stories:\n"
#         f"{story_block}\n"
#         f"\n"
#         f"STRICT CONSTRAINTS:\n"
#         f"- Use ONLY functions explicitly listed in the 'Page Object Methods' section below.\n"
#         f"- DO NOT invent, guess, or generate any method names that are not in the list.\n"
#         f"- If a certain step is not supported by the listed methods, SKIP that step (do not invent helper functions or workarounds).\n"
#         f"- Never use classes, class-based page objects, or anything imported from 'page_objects'.\n"
#         f"- DO NOT write or generate import statements.\n"
#         f"- Use only the 'page' object with the allowed POM functions (e.g., enter_username(page, \"value\")).\n"
#         f"- Do NOT write comments or explanations—output ONLY valid Python code, directly with the test function(s).\n"
#         f"\n"
#         f"YOUR TASK:\n"
#         f"- Think like an expert functional QA tester.\n"
#         f"- For the above user stories, generate ALL possible and meaningful test cases for:\n"
#         f"    1. Functional testing:\n"
#         f"       - Every relevant positive (valid), negative (invalid, missing), boundary, and alternative workflow scenario that can be covered using the available POM methods.\n"
#         f"       - Multiple test cases per feature/step if meaningful.\n"
#         f"    2. Smoke testing:\n"
#         f"       - Minimal number of tests that validate critical end-to-end flows (happy path and essential variations).\n"
#         f"       - Ensure all core workflows are covered.\n"
#         f"    3. Regression testing:\n"
#         f"       - All scenarios that could catch regressions (e.g., edge cases, blank or long field values, state changes, previously reported bugs, etc.), using only the available POM methods.\n"
#         f"- Generate as many distinct, relevant, and non-duplicate test cases as possible for each test type (functional, smoke, regression), ensuring broad and deep coverage of the user stories and workflows.\n"
#         f"- Name test functions as test_<testtype>_<scenario> (e.g., test_functional_valid_login, test_regression_blank_zipcode, test_smoke_end_to_end_checkout). Use unique, descriptive names for each case.\n"
#         f"- Each test function must use only the allowed POM methods and the 'page' object.\n"
#         f"- Do NOT define or generate any new helper functions/methods—use only those already defined in the allowed methods list.\n"
#         f"\n"
#         f"Site URL: {site_url}\n\n"
#         f"Page Object Methods:\n{page_method_section}\n\n"
#         f"Additional Hints:\n{dynamic_steps_joined}\n\n"
#         f"Test Data Guidance:\n"
#         f"- Cover normal, blank, long, special character, and invalid inputs wherever possible, based on POM method parameters.\n"
#         f"- For every mandatory field or step, cover both valid and invalid or missing paths if feasible using only allowed methods.\n"
#         f"\n"
#         f"Final Output:\n"
#         f"- Output ONLY valid Python test function code for all possible functional, smoke, and regression cases, as described above.\n"
#         f"- No comments, no markdown, no imports, no explanations—just the test functions.\n"
#         f"- Each test must use only the functions from the 'Page Object Methods' list, and must interact with the 'page' object.\n"
#         f"\n"
#         f"Begin."
#     )

# def build_prompt(
#     story_block: str,
#     method_map: dict,
#     page_names: list[str],
#     site_url: str,
#     dynamic_steps: list[str]
# ) -> str:
#     page_method_section = "\n".join(
#         f"# {p}:\n" + "\n".join(f"- def {m}" for m in method_map.get(p, [])) for p in page_names
#     )
#     dynamic_steps_joined = "\n".join(dynamic_steps)

#     return (
#         f"You are a senior QA automation engineer tasked to write Playwright Python tests for the following user stories:\n"
#         f"{story_block}\n"
#         f"\n"
#         f"STRICT CONSTRAINTS:\n"
#         f"- Use ONLY functions explicitly listed in the 'Page Object Methods' section below.\n"
#         f"- DO NOT invent, guess, or generate any method names that are not in the list.\n"
#         f"- If a certain step is not supported by the listed methods, SKIP that step (do not invent helper functions or workarounds).\n"
#         f"- Never use classes, class-based page objects, or anything imported from 'page_objects'.\n"
#         f"- DO NOT write or generate import statements.\n"
#         f"- Use only the 'page' object with the allowed POM functions (e.g., enter_username(page, \"value\")).\n"
#         f"\n"
#         f"YOUR TASK:\n"
#         f"- Think like an expert functional QA tester.\n"
#         f"- For the above user stories, generate ALL possible and meaningful test cases for:\n"
#         f"    1. Functional testing:\n"
#         f"       - Every relevant positive (valid), negative (invalid, missing), boundary, and alternative workflow scenario that can be covered using the available POM methods.\n"
#         f"       - Multiple test cases per feature/step if meaningful.\n"
#         f"    2. Smoke testing:\n"
#         f"       - Minimal number of tests that validate critical end-to-end flows (happy path and essential variations).\n"
#         f"       - Ensure all core workflows are covered.\n"
#         f"    3. Regression testing:\n"
#         f"       - All scenarios that could catch regressions (e.g., edge cases, blank or long field values, state changes, previously reported bugs, etc.), using only the available POM methods.\n"
#         f"- Generate as many distinct, relevant, and non-duplicate test cases as possible for each test type (functional, smoke, regression), ensuring broad and deep coverage of the user stories and workflows.\n"
#         f"- Name test functions as test_<testtype>_<scenario> (e.g., test_functional_valid_login, test_regression_blank_zipcode, test_smoke_end_to_end_checkout). Use unique, descriptive names for each case.\n"
#         f"- Each test function must use only the allowed POM methods and the 'page' object.\n"
#         f"- Do NOT define or generate any new helper functions/methods—use only those already defined in the allowed methods list.\n"
#         f"\n"
#         f"Site URL: {site_url}\n\n"
#         f"Page Object Methods:\n{page_method_section}\n\n"
#         f"Additional Hints:\n{dynamic_steps_joined}\n\n"
#         f"Test Data Guidance:\n"
#         f"- Cover normal, blank, long, special character, and invalid inputs wherever possible, based on POM method parameters.\n"
#         f"- For every mandatory field or step, cover both valid and invalid or missing paths if feasible using only allowed methods.\n"
#         f"\n"
#         f"IMPORTANT: For EVERY automation test function you generate, you must include a comment block immediately above the function in the following format:\n"
#         f"    # Manual Steps:\n"
#         f"    # 1. Step one\n"
#         f"    # 2. Step two\n"
#         f"    # ...\n"
#         f"These manual steps must correspond exactly to the actions covered in that test function, written in clear step-by-step language, and should match the intended scenario (functional, smoke, or regression).\n"
#         f"\n"
#         f"Final Output:\n"
#         f"- Output valid Python code for all possible functional, smoke, and regression test cases, as described above.\n"
#         f"- Each test function must have the manual steps as a comment block immediately above it.\n"
#         f"- No markdown, no explanations, no imports—just the test functions and their manual steps as comments.\n"
#         f"\n"
#         f"Begin."
#     )

# def build_prompt(
#     story_block: str,
#     method_map: dict,
#     page_names: list[str],
#     site_url: str,
#     dynamic_steps: list[str]
# ) -> str:
#     page_method_section = "\n".join(
#         f"// {p}:\n" + "\n".join(f"- function {m}" for m in method_map.get(p, [])) for p in page_names
#     )
#     dynamic_steps_joined = "\n".join(dynamic_steps)

#     return (
#         f"You are a senior QA automation engineer tasked to write Playwright TypeScript tests for the following user stories:\n"
#         f"{story_block}\n"
#         f"\n"
#         f"STRICT CONSTRAINTS:\n"
#         f"- Use ONLY functions explicitly listed in the 'Page Object Methods' section below.\n"
#         f"- DO NOT invent, guess, or generate any function names that are not in the list.\n"
#         f"- If a certain step is not supported by the listed functions, SKIP that step (do not invent helper functions or workarounds).\n"
#         f"- Never use classes, class-based page objects, or anything imported from 'page_objects'.\n"
#         f"- DO NOT write or generate import statements.\n"
#         f"- Use only the 'page' object with the allowed POM functions (e.g., await enterUsername(page, \"value\")).\n"
#         f"\n"
#         f"YOUR TASK:\n"
#         f"- Think like an expert functional QA tester.\n"
#         f"- For the above user stories, generate ALL possible and meaningful test cases for:\n"
#         f"    1. Functional testing:\n"
#         f"       - Every relevant positive (valid), negative (invalid, missing), boundary, and alternative workflow scenario that can be covered using the available POM functions.\n"
#         f"       - Multiple test cases per feature/step if meaningful.\n"
#         f"    2. Smoke testing:\n"
#         f"       - Minimal number of tests that validate critical end-to-end flows (happy path and essential variations).\n"
#         f"       - Ensure all core workflows are covered.\n"
#         f"    3. Regression testing:\n"
#         f"       - All scenarios that could catch regressions (e.g., edge cases, blank or long field values, state changes, previously reported bugs, etc.), using only the available POM functions.\n"
#         f"- Generate as many distinct, relevant, and non-duplicate test cases as possible for each test type (functional, smoke, regression), ensuring broad and deep coverage of the user stories and workflows.\n"
#         f"- Name test functions as test<TypeType><Scenario> (e.g., testFunctionalValidLogin, testRegressionBlankZipcode, testSmokeEndToEndCheckout). Use unique, descriptive names for each case, following TypeScript camelCase naming conventions.\n"
#         f"- Each test function must use only the allowed POM functions and the 'page' object.\n"
#         f"- Do NOT define or generate any new helper functions/methods—use only those already defined in the allowed functions list.\n"
#         f"\n"
#         f"Site URL: {site_url}\n\n"
#         f"// Page Object Methods:\n{page_method_section}\n\n"
#         f"// Additional Hints:\n{dynamic_steps_joined}\n\n"
#         f"// Test Data Guidance:\n"
#         f"// - Cover normal, blank, long, special character, and invalid inputs wherever possible, based on POM function parameters.\n"
#         f"// - For every mandatory field or step, cover both valid and invalid or missing paths if feasible using only allowed functions.\n"
#         f"\n"
#         f"IMPORTANT: For EVERY automation test function you generate, you must include a comment block immediately above the function in the following format:\n"
#         f"    // Manual Steps:\n"
#         f"    // 1. Step one\n"
#         f"    // 2. Step two\n"
#         f"    // ...\n"
#         f"These manual steps must correspond exactly to the actions covered in that test function, written in clear step-by-step language, and should match the intended scenario (functional, smoke, or regression).\n"
#         f"\n"
#         f"Final Output:\n"
#         f"- Output valid **TypeScript** code for all possible functional, smoke, and regression test cases, as described above.\n"
#         f"- Each test function must have the manual steps as a comment block immediately above it.\n"
#         f"- No markdown, no explanations, no imports—just the test functions and their manual steps as comments.\n"
#         f"\n"
#         f"Begin."
#     )



# def build_prompt(
#     story_block: str,
#     method_map: dict,
#     page_names: list[str],
#     site_url: str,
#     dynamic_steps: list[str]
# ) -> str:
#     page_method_section = "\n".join(
#         f"# {p}:\n" + "\n".join(f"- def {m}" for m in method_map.get(p, [])) for p in page_names
#     )
#     dynamic_steps_joined = "\n".join(dynamic_steps)

#     return (
#         f"You are a senior QA automation engineer tasked to write Playwright Python tests for the following user stories:\n"
#         f"{story_block}\n"
#         f"\n"
#         f"⚠️ MANDATORY CONSTRAINTS:\n"
#         f"- Use ONLY the functions listed in the 'Page Object Methods' section below.\n"
#         f"- NEVER invent, guess, or create method names not explicitly listed.\n"
#         f"- If a step has no matching method, include a comment like `# Skipped step due to missing method: <step description>`.\n"
#         f"- DO NOT use any classes or class-based page objects. Only use functions with `(page, ...)` signature.\n"
#         f"\n"
#         f"📌 TEST GENERATION REQUIREMENT:\n"
#         f"- For each individual PAGE listed below, generate three test functions:\n"
#         f"  * Positive: Typical correct input scenario.\n"
#         f"  * Negative: Invalid or missing data.\n"
#         f"  * Edge: Boundary or extreme input (e.g. long strings, special characters).\n"
#         f"- Do NOT merge steps across pages. Each test should be scoped to its corresponding page.\n"
#         f"- This ensures we have **3 test functions per page** regardless of story length.\n"
#         f"- If any page is not relevant to the user story, still attempt to generate logical edge/negative tests for that page's methods.\n"
#         f"\n"
#         f"- Name test functions as: `test_positive_<page_name>_flow`, `test_negative_<page_name>_flow`, `test_edge_<page_name>_flow`.\n"
#         f"- Call all functions using the `page` object (e.g., `fill_username(page, \"value\")`).\n"
#         f"- DO NOT generate any helper methods, import statements, markdown, or extra text.\n"
#         f"\n"
#         f"Site URL: {site_url}\n\n"
#         f"📄 Page Object Methods:\n{page_method_section}\n\n"
#         f"💡 Additional Hints:\n{dynamic_steps_joined}\n\n"
#         f"Generate the code for all three test cases for each page below."
#     )

# def build_prompt(
#     story_block: str,
#     method_map: dict,
#     page_names: list[str],
#     site_url: str,
#     dynamic_steps: list[str]
# ) -> str:
#     page_method_section = "\n".join(
#         f"# {p}:\n" + "\n".join(f"- def {m}" for m in method_map.get(p, [])) for p in page_names
#     )
#     dynamic_steps_joined = "\n".join(dynamic_steps)

#     return (
#         f"You are a senior QA automation engineer tasked to write Playwright Python tests for the following user story:\n"
#         f"{story_block}\n"
#         f"\n"
#         f"⚠️ MANDATORY CONSTRAINTS:\n"
#         f"- Use ONLY functions listed in the 'Page Object Methods' section.\n"
#         f"- NEVER invent, guess, or create method names not explicitly listed.\n"
#         f"- If a step has no matching method, add comment `# Skipped step due to missing method: <step description>`.\n"
#         f"- DO NOT use classes; ONLY use functions with `(page, ...)` signatures.\n"
#         f"\n"
#         f"📌 TEST GENERATION REQUIREMENTS (VERY IMPORTANT):\n"
#         f"For each individual PAGE listed, generate three test functions (positive, negative, edge).\n"
#         f"Each test MUST start from the beginning (open URL '{site_url}') and INCLUDE ALL NECESSARY PREREQUISITE STEPS (like login, navigation, adding items to cart, etc.) to logically reach the page under test.\n"
#         f"Prerequisite steps for each page are as follows:\n"
#         f"  - login: Navigate to URL first.\n"
#         f"  - inventory: Navigate to URL, then login.\n"
#         f"  - cart: Navigate to URL, login, add at least one product to cart.\n"
#         f"  - checkout_info: Navigate to URL, login, add at least one product to cart, go to cart, click checkout.\n"
#         f"  - checkout_overview: Navigate to URL, login, add product, go to cart, click checkout, fill checkout info, click continue.\n"
#         f"\n"
#         f"⚠️ DO NOT SKIP these prerequisite steps, always clearly include them at the beginning of each test function.\n"
#         f"⚠️ Ensure each test function fully tests the listed methods for the corresponding page after reaching it.\n"
#         f"\n"
#         f"Name each test function as follows:\n"
#         f"- `test_positive_<page_name>_flow`\n"
#         f"- `test_negative_<page_name>_flow`\n"
#         f"- `test_edge_<page_name>_flow`\n"
#         f"\n"
#         f"Use the 'page' object for all method calls (e.g., `fill_username(page, 'value')`).\n"
#         f"DO NOT generate imports, markdown, explanations, or extra text—output ONLY valid Python code.\n"
#         f"\n"
#         f"Site URL: {site_url}\n\n"
#         f"📄 Page Object Methods:\n{page_method_section}\n\n"
#         f"💡 Additional Hints:\n{dynamic_steps_joined}\n\n"
#         f"Generate the code for all three test cases for each page below."
#     )

