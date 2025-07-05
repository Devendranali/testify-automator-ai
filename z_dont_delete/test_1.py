

# from playwright.sync_api import sync_playwright
# from pages.saucedemo_cart_page_methods import *
# from pages.saucedemo_checkout_info_page_methods import *
# from pages.saucedemo_checkout_overview_page_methods import *
# from pages.saucedemo_inventory_page_methods import *
# from pages.saucedemo_login_page_methods import *
# import time


# def test_positive_login_and_order_flow(page):
#     page.goto("https://www.saucedemo.com")
#     verify_swag_labs(page)
#     enter_username(page, "standard_user")
#     enter_password(page, "secret_sauce")
#     click_login(page)
#     verify_products(page)
#     click_add_to_cart(page)
#     verify_your_cart(page)
#     click_checkout(page)
#     verify_checkout_your_information(page)
#     enter_first_name(page, "John")
#     enter_last_name(page, "Doe")
#     enter_zip_postal_code(page, "12345")
#     click_continue(page)
#     verify_checkout_overview(page)
#     click_finish(page)


# def test_negative_login_and_order_flow(page):
#     page.goto("https://www.saucedemo.com")
#     verify_swag_labs(page)
#     enter_username(page, "invalid_user")
#     enter_password(page, "wrong_password")
#     click_login(page)
#     verify_error_user(page)


# def test_edge_login_and_order_flow(page):
#     page.goto("https://www.saucedemo.com")
#     verify_swag_labs(page)
#     enter_username(page, "")
#     enter_password(page, "secret_sauce")
#     click_login(page)
#     verify_error_user(page)

# # --------------------------------------------------------------------------------

# def test_positive_login_and_order_flow():
#     p, browser, page = setup_page()

#     try:
#         verify_swag_labs(page)
#         print("✅ Verified Swag Labs")
#     except Exception as e:
#         print(f"❌ Failed: verify_swag_labs — {e}")
#     time.sleep(1)

#     try:
#         enter_username(page, "standard_user")
#         print("✅ Entered username")
#     except Exception as e:
#         print(f"❌ Failed: enter_username — {e}")
#     time.sleep(1)

#     try:
#         enter_password(page, "secret_sauce")
#         print("✅ Entered password")
#     except Exception as e:
#         print(f"❌ Failed: enter_password — {e}")
#     time.sleep(1)

#     try:
#         click_login(page)
#         print("✅ Clicked login")
#     except Exception as e:
#         print(f"❌ Failed: click_login — {e}")
#     time.sleep(1)

#     try:
#         verify_products(page)
#         print("✅ Verified Products page")
#     except Exception as e:
#         print(f"❌ Failed: verify_products — {e}")
#     time.sleep(1)

#     try:
#         click_add_to_cart(page)
#         print("✅ Clicked Add to Cart")
#     except Exception as e:
#         print(f"❌ Failed: click_add_to_cart — {e}")
#     time.sleep(1)

#     try:
#         verify_your_cart(page)
#         print("✅ Verified Your Cart")
#     except Exception as e:
#         print(f"❌ Failed: verify_your_cart — {e}")
#     time.sleep(1)

#     try:
#         click_checkout(page)
#         print("✅ Clicked Checkout")
#     except Exception as e:
#         print(f"❌ Failed: click_checkout — {e}")
#     time.sleep(1)

#     try:
#         verify_checkout_your_information(page)
#         print("✅ Verified Checkout Info Page")
#     except Exception as e:
#         print(f"❌ Failed: verify_checkout_your_information — {e}")
#     time.sleep(1)

#     try:
#         enter_first_name(page, "John")
#         enter_last_name(page, "Doe")
#         enter_zip_postal_code(page, "12345")
#         print("✅ Entered user info")
#     except Exception as e:
#         print(f"❌ Failed: enter user info — {e}")
#     time.sleep(1)

#     try:
#         click_continue(page)
#         print("✅ Clicked Continue")
#     except Exception as e:
#         print(f"❌ Failed: click_continue — {e}")
#     time.sleep(1)

#     try:
#         verify_checkout_overview(page)
#         print("✅ Verified Checkout Overview")
#     except Exception as e:
#         print(f"❌ Failed: verify_checkout_overview — {e}")
#     time.sleep(1)

#     try:
#         click_finish(page)
#         print("✅ Clicked Finish")
#     except Exception as e:
#         print(f"❌ Failed: click_finish — {e}")
#     time.sleep(1)

#     browser.close()
#     p.stop()

# def test_negative_login_and_order_flow():
#     p, browser, page = setup_page()

#     try:
#         verify_swag_labs(page)
#         print("✅ Verified Swag Labs")
#     except Exception as e:
#         print(f"❌ Failed: verify_swag_labs — {e}")
#     time.sleep(1)

#     try:
#         enter_username(page, "invalid_user")
#         print("✅ Entered invalid username")
#     except Exception as e:
#         print(f"❌ Failed: enter_username — {e}")
#     time.sleep(1)

#     try:
#         enter_password(page, "wrong_password")
#         print("✅ Entered wrong password")
#     except Exception as e:
#         print(f"❌ Failed: enter_password — {e}")
#     time.sleep(1)

#     try:
#         click_login(page)
#         print("✅ Clicked login")
#     except Exception as e:
#         print(f"❌ Failed: click_login — {e}")
#     time.sleep(1)

#     try:
#         verify_error_user(page)
#         print("✅ Verified error message")
#     except Exception as e:
#         print(f"❌ Failed: verify_error_user — {e}")
#     time.sleep(1)

#     browser.close()
#     p.stop()

# def test_edge_login_and_order_flow():
#     p, browser, page = setup_page()

#     try:
#         verify_swag_labs(page)
#         print("✅ Verified Swag Labs")
#     except Exception as e:
#         print(f"❌ Failed: verify_swag_labs — {e}")
#     time.sleep(1)

#     try:
#         enter_username(page, "")
#         print("✅ Left username blank")
#     except Exception as e:
#         print(f"❌ Failed: enter_username — {e}")
#     time.sleep(1)

#     try:
#         enter_password(page, "secret_sauce")
#         print("✅ Entered password")
#     except Exception as e:
#         print(f"❌ Failed: enter_password — {e}")
#     time.sleep(1)

#     try:
#         click_login(page)
#         print("✅ Clicked login")
#     except Exception as e:
#         print(f"❌ Failed: click_login — {e}")
#     time.sleep(1)

#     try:
#         verify_error_user(page)
#         print("✅ Verified error message for blank username")
#     except Exception as e:
#         print(f"❌ Failed: verify_error_user — {e}")
#     time.sleep(1)

#     browser.close()
#     p.stop()

# def setup_page():
#     from playwright.sync_api import sync_playwright
#     from pathlib import Path
#     import json
#     from lib.smart_ai import patch_page_with_smartai

#     p = sync_playwright().start()
#     browser = p.chromium.launch(headless=False)
#     page = browser.new_page()
#     page.goto("https://www.saucedemo.com")

#     script_dir = Path(__file__).parent
#     metadata_path = (script_dir.parent / "metadata" / "after_enrichment.json").resolve()
#     print("Loading:", metadata_path)

#     with open(metadata_path, "r") as f:
#         metadata = json.load(f)

#     patch_page_with_smartai(page, metadata)
#     return p, browser, page

# # ---------------------------------------------------------------------------------


# ======================================= ASYNC VERSION ===========================================
# import asyncio
# import json
# from pathlib import Path

# import pytest
# from playwright.async_api import async_playwright

# from pages.saucedemo_cart_page_methods import *
# from pages.saucedemo_checkout_info_page_methods import *
# from pages.saucedemo_checkout_overview_page_methods import *
# from pages.saucedemo_inventory_page_methods import *
# from pages.saucedemo_login_page_methods import *
# from lib.smart_ai import patch_page_with_smartai


# async def setup_page():
#     playwright = await async_playwright().start()
#     browser = await playwright.chromium.launch(headless=False)
#     page = await browser.new_page()
#     await page.goto("https://www.saucedemo.com")

#     script_dir = Path(__file__).parent
#     metadata_path = (script_dir.parent / "metadata" / "after_enrichment.json").resolve()
#     print("Loading:", metadata_path)

#     with open(metadata_path, "r") as f:
#         metadata = json.load(f)

#     patch_page_with_smartai(page, metadata)
#     return playwright, browser, page

# @pytest.mark.asyncio
# async def test_positive_login_and_order_flow():
#     p, browser, page = await setup_page()

#     try:
#         await verify_swag_labs(page)
#         print("✅ Verified Swag Labs")

#         await enter_username(page, "standard_user")
#         print("✅ Entered username")

#         await enter_password(page, "secret_sauce")
#         print("✅ Entered password")

#         await click_login(page)
#         print("✅ Clicked login")

#         await verify_products(page)
#         print("✅ Verified Products page")

#         await click_add_to_cart(page)
#         print("✅ Clicked Add to Cart")

#         await verify_your_cart(page)
#         print("✅ Verified Your Cart")

#         await click_checkout(page)
#         print("✅ Clicked Checkout")

#         await verify_checkout_your_information(page)
#         print("✅ Verified Checkout Info Page")

#         await enter_first_name(page, "John")
#         await enter_last_name(page, "Doe")
#         await enter_zip_postal_code(page, "12345")
#         print("✅ Entered user info")

#         await click_continue(page)
#         print("✅ Clicked Continue")

#         await verify_checkout_overview(page)
#         print("✅ Verified Checkout Overview")

#         await click_finish(page)
#         print("✅ Clicked Finish")

#     except Exception as e:
#         print(f"❌ Failed: {e}")
#     finally:
#         await browser.close()
#         await p.stop()

# @pytest.mark.asyncio
# async def test_negative_login_and_order_flow():
#     p, browser, page = await setup_page()

#     try:
#         await verify_swag_labs(page)
#         print("✅ Verified Swag Labs")

#         await enter_username(page, "invalid_user")
#         print("✅ Entered invalid username")

#         await enter_password(page, "wrong_password")
#         print("✅ Entered wrong password")

#         await click_login(page)
#         print("✅ Clicked login")

#         await verify_error_user(page)
#         print("✅ Verified error message")

#     except Exception as e:
#         print(f"❌ Failed: {e}")
#     finally:
#         await browser.close()
#         await p.stop()


# @pytest.mark.asyncio
# async def test_edge_login_and_order_flow():
#     p, browser, page = await setup_page()

#     try:
#         await verify_swag_labs(page)
#         print("✅ Verified Swag Labs")

#         await enter_username(page, "")
#         print("✅ Left username blank")

#         await enter_password(page, "secret_sauce")
#         print("✅ Entered password")

#         await click_login(page)
#         print("✅ Clicked login")

#         await verify_error_user(page)
#         print("✅ Verified error message for blank username")

#     except Exception as e:
#         print(f"❌ Failed: {e}")
#     finally:
#         await browser.close()
#         await p.stop()
