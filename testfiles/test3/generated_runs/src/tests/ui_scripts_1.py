import asyncio
from playwright.async_api import async_playwright
from generated_runs.src.pages.base_page import BasePage
from generated_runs.src.pages.dashboard_page import DashboardPage
from generated_runs.src.pages.customers_page import CustomersPage

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        base_page = BasePage(page, "base", url='https://preview--bank-buddy-crm-react.lovable.app/')
        await base_page.goto()
        customers_page = CustomersPage(page, "customers")
        dashboard_page = DashboardPage(page, "dashboard")

        await dashboard_page.verify_bank_crm_visible()
        await dashboard_page.click_customers()
        await customers_page.click_new_customer()
        await customers_page.enter_full_name_input("John Doe")
        await customers_page.enter_email_input("john.doe@example.com")
        await customers_page.enter_phone_number_input("1234567890")
        await customers_page.select_select_account_type("Standard")
        await customers_page.enter_address_input("123 Main St, Anytown, USA")
        await customers_page.enter_occupation_input("Software Engineer")
        await customers_page.enter_annual_income_input("75000")
        await customers_page.enter_initial_deposit_input("1000")
        await customers_page.click_add_customer()
        await dashboard_page.verify_john_doe_visible()

if __name__ == "__main__":
    asyncio.run(main())
