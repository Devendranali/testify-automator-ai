from lib.smart_ai import patch_page_with_smartai

# Methods for page: dashboard

def enter_search_customers_loans_transactions(page, value):
    page.smartAI('dashboard_search_search_customers,_loans,_transactions..._textbox').fill(value)

def verify_dashboard_visible(page):
    assert page.smartAI('dashboard_title_dashboard_label').is_visible()

def verify_bank_crmnavigationdashboardcustomersloanstransactionstasksreportsanalyticssettingstoggle_sidebarjohn_doedashboardwelcome_back_here_s_your_banking_overview_export_reporttotal_customers2_847_12_5_from_last_monthactive_loans_45_2m_8_2_from_last_monthmonthly_transactions18_394_15_3_from_last_monthrevenue_growth23_4_2_1_from_last_monthloan_portfolio_trendmonthly_loan_disbursements_over_the_last_6_monthsjanfebmaraprmayjun01500000300000045000006000000customer_distributioncustomer_segments_by_account_typepremium_35_standard_45_basic_20_recent_activitieslatest_customer_interactions_and_transactionssarah_johnsonloan_application_approved_250_0002_hours_agomichael_chenaccount_verification_pending_4_hours_agoemma_davislarge_transaction_alert_75_0006_hours_agorobert_wilsonmonthly_payment_received_3_2008_hours_ago_visible(page):
    assert page.smartAI('dashboard_greeting_welcome_back!_heres_your_banking_overview._label').is_visible()

def click_export_report(page):
    page.smartAI('dashboard_export_export_report_button').click()

def verify_total_customers_visible(page):
    assert page.smartAI('dashboard_info_header_total_customers_label').is_visible()

def verify_from_last_month_visible(page):
    assert page.smartAI('dashboard_growth_info_+12.5%_from_last_month_label').is_visible()

def verify_active_loans_visible(page):
    assert page.smartAI('dashboard_info_header_active_loans_label').is_visible()

def verify_standard_45_visible(page):
    assert page.smartAI('dashboard_active_loans_$45.2m_label').is_visible()

def verify_monthly_transactions_visible(page):
    assert page.smartAI('dashboard_info_header_monthly_transactions_label').is_visible()

def verify_revenue_growth_visible(page):
    assert page.smartAI('dashboard_info_header_revenue_growth_label').is_visible()

def verify_loan_portfolio_trend_visible(page):
    assert page.smartAI('dashboard_chart_title_loan_portfolio_trend_label').is_visible()

def verify_monthly_loan_disbursements_over_the_last_6_months_visible(page):
    assert page.smartAI('dashboard_chart_info_monthly_loan_disbursements_over_the_last_6_months_label').is_visible()

def verify_customer_distribution_visible(page):
    assert page.smartAI('dashboard_chart_title_customer_distribution_label').is_visible()

def verify_customer_segments_by_account_type_visible(page):
    assert page.smartAI('dashboard_chart_info_customer_segments_by_account_type_label').is_visible()

def verify_premium_35_visible(page):
    assert page.smartAI('dashboard_customer_segment_premium_35%_label').is_visible()

def verify_standard_45_visible(page):
    assert page.smartAI('dashboard_customer_segment_standard_45%_label').is_visible()

def verify_basic_20_visible(page):
    assert page.smartAI('dashboard_customer_segment_basic_20%_label').is_visible()

def click_customers(page):
    page.smartAI('dashboard__customers_link').click()
