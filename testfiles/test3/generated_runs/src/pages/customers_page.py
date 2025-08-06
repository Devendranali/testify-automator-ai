from generated_runs.src.pages.base_page import BasePage
from services.page_enricher import enrich_page
from generated_runs.src.lib.smart_ai import patch_page_with_smartai
from utils.enrichment_status import is_enriched

class CustomersPage(BasePage):
    def __init__(self, page, page_name="customers"):
        super().__init__(page, page_name)
        self._enriched = False
        metadata = self._fetch_metadata_from_chroma(page_name)
        patch_page_with_smartai(self.page, metadata)

    async def _enrich_if_needed(self, force=False):
        if force or not is_enriched(self.page_name):
            await enrich_page(self.page, self.page_name)
            self._enriched = True

    async def click_navigation(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_button_navigation_6ab61bef')
        await locator.click()

    async def enter_search_customers_loans_transactions(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_search_customers,_loans,_transactions..._textbox_search_be73039f')
        await locator.fill(value)

    async def click_dashboard(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_dashboard_button_navigation_fb22376c')
        await locator.click()

    async def click_customers(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_customers_button_navigation_62cd2bf8')
        await locator.click()

    async def click_loans(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_loans_button_navigation_f083cd47')
        await locator.click()

    async def click_transactions(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_transactions_button_navigation_bb833203')
        await locator.click()

    async def click_tasks(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_tasks_button_navigation_63e52ff9')
        await locator.click()

    async def click_reports(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_reports_button_navigation_1dc35b9f')
        await locator.click()

    async def click_analytics(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_analytics_button_navigation_8227d101')
        await locator.click()

    async def click_settings(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_settings_button_navigation_9de99b8a')
        await locator.click()

    async def verify_customers_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_customers_label_section_title_2ec8510a')
        assert await locator.is_visible()

    async def verify_manage_your_customer_relationships_and_accounts_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_manage_your_customer_relationships_and_accounts_label_section_info_f20c0595')
        assert await locator.is_visible()

    async def enter_search_customers(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_search_customers..._textbox_search_85d3ce1f')
        await locator.fill(value)

    async def click_filters(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_filters_button_filter_4c0a3d63')
        await locator.click()

    async def verify_customer_list_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_customer_list_label_section_title_ad47eb6a')
        assert await locator.is_visible()

    async def verify_3_customers_found_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_3_customers_found_label_section_info_f58e240e')
        assert await locator.is_visible()

    async def verify_customer_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_customer_label_column_title_01dacf22')
        assert await locator.is_visible()

    async def verify_account_type_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_account_type_label_column_title_1b2a9c41')
        assert await locator.is_visible()

    async def verify_balance_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_balance_label_column_title_a5832ecf')
        assert await locator.is_visible()

    async def verify_status_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_status_label_column_title_b24a10b1')
        assert await locator.is_visible()

    async def verify_join_date_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_join_date_label_column_title_c808519b')
        assert await locator.is_visible()

    async def verify_actions_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_actions_label_column_title_32bd0b21')
        assert await locator.is_visible()

    async def verify_sarah_johnson_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_sarah_johnson_label_customer_name_91134cc9')
        assert await locator.is_visible()

    async def verify_sarah_johnson_email_com_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_sarah.johnson@email.com_label_customer_email_ea79968a')
        assert await locator.is_visible()

    async def verify_premium_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_premium_label_account_type_c1ae4279')
        assert await locator.is_visible()

    async def verify_1_45_000_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_$1,45,000_label_balance_dc74e6a8')
        assert await locator.is_visible()

    async def verify_active_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_active_label_status_5fc1bbb1')
        assert await locator.is_visible()

    async def verify_2023_01_15_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_2023-01-15_label_join_date_13b4a3e0')
        assert await locator.is_visible()

    async def click_view_action(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_button_view_action_cc60ce91')
        await locator.click()

    async def click_edit_action(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_button_edit_action_d3d0df61')
        await locator.click()

    async def verify_michael_chen_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_michael_chen_label_customer_name_8dbd8345')
        assert await locator.is_visible()

    async def verify_michael_chen_email_com_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_michael.chen@email.com_label_customer_email_8f50f16b')
        assert await locator.is_visible()

    async def verify_standard_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_standard_label_account_type_ef9be216')
        assert await locator.is_visible()

    async def verify_52_000_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_$52,000_label_balance_b6e2bd67')
        assert await locator.is_visible()

    async def verify_2023_03_22_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_2023-03-22_label_join_date_363240e3')
        assert await locator.is_visible()

    async def verify_emma_davis_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_emma_davis_label_customer_name_671b9ccd')
        assert await locator.is_visible()

    async def verify_emma_davis_email_com_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_emma.davis@email.com_label_customer_email_1680f20b')
        assert await locator.is_visible()

    async def verify_89_000_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_$89,000_label_balance_f3422319')
        assert await locator.is_visible()

    async def verify_2022_11_08_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_2022-11-08_label_join_date_bcd7c000')
        assert await locator.is_visible()

    async def click_export(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_export_button_export_ec306f18')
        await locator.click()

    async def click_new_customer(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_+_new_customer_button_add_customer_e84a62b3')
        await locator.click()

    async def click_edit_with(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_edit_with_button_edit_action_78ed448f')
        await locator.click()

    async def verify_add_new_customer_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_add_new_customer_label_form_title_2b3b0780')
        assert await locator.is_visible()

    async def verify_enter_the_customer_details_to_create_a_new_account_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_enter_the_customer_details_to_create_a_new_account._label_form_instruction_4e368c65')
        assert await locator.is_visible()

    async def verify_full_name_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_full_name_label_full_name_label_7fa7eb35')
        assert await locator.is_visible()

    async def enter_full_name_input(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_textbox_full_name_input_b5555c13')
        await locator.fill(value)

    async def verify_email_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_email_label_email_label_1e22d7f0')
        assert await locator.is_visible()

    async def enter_email_input(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_textbox_email_input_b7f01675')
        await locator.fill(value)

    async def verify_phone_number_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_phone_number_label_phone_number_label_03e465fd')
        assert await locator.is_visible()

    async def enter_phone_number_input(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_textbox_phone_number_input_bb72a72b')
        await locator.fill(value)

    async def select_select_account_type(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_select_account_type_select_account_type_select_739bf8ef')
        await locator.select_option(value)

    async def verify_address_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_address_label_address_label_bfa99020')
        assert await locator.is_visible()

    async def enter_address_input(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_textbox_address_input_0da1bba0')
        await locator.fill(value)

    async def verify_occupation_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_occupation_label_occupation_label_78041ebe')
        assert await locator.is_visible()

    async def enter_occupation_input(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_textbox_occupation_input_7c88216e')
        await locator.fill(value)

    async def verify_annual_income_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_annual_income_label_annual_income_label_41327b0b')
        assert await locator.is_visible()

    async def enter_annual_income_input(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_textbox_annual_income_input_7b960691')
        await locator.fill(value)

    async def verify_initial_deposit_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_initial_deposit_label_initial_deposit_label_a98dd99a')
        assert await locator.is_visible()

    async def enter_initial_deposit_input(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_textbox_initial_deposit_input_842f44e3')
        await locator.fill(value)

    async def click_cancel(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_cancel_button_cancel_71a3913d')
        await locator.click()

    async def click_add_customer(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_add_customer_button_submit_bce56d38')
        await locator.click()
