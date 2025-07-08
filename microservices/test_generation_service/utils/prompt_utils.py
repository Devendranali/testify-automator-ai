# utils/prompt_utils.py
from typing import List

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