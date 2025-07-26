def build_method_prompt_block(method_map: dict) -> str:
    """
    Converts { "login": ["enter_username", "click_login"] }
    → string:
    login_page:
      - enter_username
      - click_login
    """
    lines = []
    for page, methods in method_map.items():
        lines.append(f"{page}_page:")
        for m in methods:
            lines.append(f"  - {m}")
    return "\n".join(lines)


def build_prompt(
    story_block: str,
    method_map: dict,
    page_names: list[str],
    site_url: str,
    dynamic_steps: list[str]
) -> str:
    page_method_section = build_method_prompt_block(method_map)
    dynamic_steps_joined = "\n".join(dynamic_steps)

    return (
        f"You are an expert QA automation engineer.\n"
        f"Generate **Playwright async Python test cases** using the provided user story.\n\n"
        f"User Story:\n{story_block}\n\n"
        f"⚠️ STRICT RULES:\n"
        f"- Use ONLY the methods listed in the Pages and Methods section below.\n"
        f"- NEVER make up method names.\n"
        f"- Each method call must start with the correct page object variable (e.g. `await login_page.enter_username(...)`).\n"
        f"- Import only required pages. Use `LoginPage(page)`, `DashboardPage(page)` etc.\n"
        f"- Assign each imported class to a variable with `_page` suffix.\n"
        f"- Use the following naming pattern:\n"
        f"  e.g. `login_page = LoginPage(page)`\n\n"
        f"🚀 OUTPUT FORMAT:\n"
        f"- Write 3 test functions: test_positive_<feature>, test_negative_<feature>, test_edge_<feature>.\n"
        f"- Use async def and Playwright's sync idioms.\n"
        f"- Use `try/except` inside each test and print pass/fail messages.\n"
        f"- Start each test by navigating to: `{site_url}`\n"
        f"- Use proper async/await for all method calls.\n"
        f"- Do NOT include markdown, explanation, or imports.\n"
        f"- Output only raw Python code with the test functions.\n\n"
        f"📘 Pages and Methods:\n{page_method_section}\n\n"
        f"💡 Additional Hints:\n{dynamic_steps_joined}\n\n"
        f"Generate the full test code now."
    )
