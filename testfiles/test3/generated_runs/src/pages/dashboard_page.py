from generated_runs.src.pages.base_page import BasePage
from services.page_enricher import enrich_page
from generated_runs.src.lib.smart_ai import patch_page_with_smartai
from utils.enrichment_status import is_enriched

class DashboardPage(BasePage):
    def __init__(self, page=None, page_name="dashboard"):
        super().__init__(page, page_name)
        self._enriched = False
        metadata = self._fetch_metadata_from_chroma(page_name)
        patch_page_with_smartai(self.page, metadata)

    async def _enrich_if_needed(self, force=False):
        if force or not is_enriched(self.page_name):
            await enrich_page(self.page, self.page_name)
            self._enriched = True

    async def verify_bank_crm_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_bank_crm_label_app_name_386d51e4')
        assert await locator.is_visible()

    async def click_dashboard(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_dashboard_button_navigation_83914516')
        await locator.click()

    async def click_customers(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_customers_button_navigation_bb4303b6')
        await locator.click()

    async def click_loans(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_loans_button_navigation_42436e2a')
        await locator.click()

    async def click_transactions(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_transactions_button_navigation_f0479a72')
        await locator.click()

    async def click_tasks(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_tasks_button_navigation_cde2a4d6')
        await locator.click()

    async def click_reports(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_reports_button_navigation_578fb659')
        await locator.click()

    async def click_analytics(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_analytics_button_navigation_49884ab5')
        await locator.click()

    async def click_settings(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_settings_button_navigation_7a36fd5d')
        await locator.click()

    async def enter_search_customers_loans_transactions(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_search_customers,_loans,_transactions..._textbox_search_3310a968')
        await locator.fill(value)

    async def verify_dashboard_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_dashboard_label_page_title_a353b4f0')
        assert await locator.is_visible()

    async def verify_welcome_back_here_s_your_banking_overview_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_welcome_back!_heres_your_banking_overview._label_page_description_09bbc2b8')
        assert await locator.is_visible()

    async def verify_total_customers_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_total_customers_label_stat_title_179d38df')
        assert await locator.is_visible()

    async def verify_2_847_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_2,847_label_stat_value_87cbb334')
        assert await locator.is_visible()

    async def verify_active_loans_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_active_loans_label_stat_title_d483020f')
        assert await locator.is_visible()

    async def verify_45_2m_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_$45.2m_label_stat_value_4d719f7e')
        assert await locator.is_visible()

    async def verify_monthly_transactions_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_monthly_transactions_label_stat_title_c5add703')
        assert await locator.is_visible()

    async def verify_18_394_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_18,394_label_stat_value_e3b013e0')
        assert await locator.is_visible()

    async def verify_revenue_growth_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_revenue_growth_label_stat_title_d31f3890')
        assert await locator.is_visible()

    async def verify_23_4_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_23.4%_label_stat_value_71ed5bf4')
        assert await locator.is_visible()

    async def click_export_report(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_export_report_button_export_ed26f6d4')
        await locator.click()

    async def verify_loan_portfolio_trend_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_loan_portfolio_trend_label_chart_title_989237db')
        assert await locator.is_visible()

    async def verify_monthly_loan_disbursements_over_the_last_6_months_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_monthly_loan_disbursements_over_the_last_6_months_label_chart_description_f35a06c8')
        assert await locator.is_visible()

    async def verify_customer_distribution_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_customer_distribution_label_chart_title_e474f1f6')
        assert await locator.is_visible()

    async def verify_customer_segments_by_account_type_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_customer_segments_by_account_type_label_chart_description_0c3ccf15')
        assert await locator.is_visible()

    async def verify_recent_activities_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_recent_activities_label_section_title_c5dd6139')
        assert await locator.is_visible()

    async def verify_latest_customer_interactions_and_transactions_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_latest_customer_interactions_and_transactions_label_section_description_80065ec9')
        assert await locator.is_visible()

    async def verify_sarah_johnson_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_sarah_johnson_label_activity_name_0c1c1c63')
        assert await locator.is_visible()

    async def verify_loan_application_approved_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_loan_application_approved_label_activity_description_9c02eed4')
        assert await locator.is_visible()

    async def verify_michael_chen_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_michael_chen_label_activity_name_f450c443')
        assert await locator.is_visible()

    async def verify_250_000_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_-_$250,000_label_activity_value_62d6508e')
        assert await locator.is_visible()

    async def verify_2_hours_ago_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_2_hours_ago_label_activity_time_03a0319c')
        assert await locator.is_visible()

    async def verify_john_doe_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_john_doe_label_user_profile_fda748b0')
        assert await locator.is_visible()

    async def click_edit_with(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_edit_with_button_edit_b26551b3')
        await locator.click()
