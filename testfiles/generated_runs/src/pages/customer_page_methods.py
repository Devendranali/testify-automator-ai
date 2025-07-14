from lib.smart_ai import patch_page_with_smartai

# Methods for page: customer

def verify_add_customer_visible(page):
    assert page.smartAI('customer_form_title_1._**add_new_customer**_label').is_visible()

def verify_add_customer_visible(page):
    assert page.smartAI('customer_form_instructions_2._**enter_the_customer_details_to_create_a_new_ac_label').is_visible()

def verify_full_name_visible(page):
    assert page.smartAI('customer_full_name_label_3._**full_name_***_label').is_visible()

def enter_full_name(page, value):
    page.smartAI('customer_full_name_input_4._[textbox_under_full_name]_textbox').fill(value)

def verify_email_visible(page):
    assert page.smartAI('customer_email_label_5._**email_***_label').is_visible()

def enter_email(page, value):
    page.smartAI('customer_email_input_6._[textbox_under_email]_textbox').fill(value)

def verify_phone_number_visible(page):
    assert page.smartAI('customer_phone_number_label_7._**phone_number_***_label').is_visible()

def enter_phone_number(page, value):
    page.smartAI('customer_phone_number_input_8._[textbox_under_phone_number]_textbox').fill(value)

def verify_select_account_type_visible(page):
    assert page.smartAI('customer_account_type_label_9._**account_type_***_label').is_visible()

def select_select_account_type(page, value):
    page.smartAI('customer_account_type_select_10._[dropdown_under_account_type]_select').select_option(value)

def verify_address_visible(page):
    assert page.smartAI('customer_address_label_11._**address**_label').is_visible()

def enter_address(page, value):
    page.smartAI('customer_address_input_12._[text_area_under_address]_textbox').fill(value)

def verify_occupation_visible(page):
    assert page.smartAI('customer_occupation_label_13._**occupation**_label').is_visible()

def enter_occupation(page, value):
    page.smartAI('customer_occupation_input_14._[textbox_under_occupation]_textbox').fill(value)

def verify_annual_income_visible(page):
    assert page.smartAI('customer_annual_income_label_15._**annual_income**_label').is_visible()

def enter_annual_income(page, value):
    page.smartAI('customer_annual_income_input_16._[textbox_under_annual_income]_textbox').fill(value)

def verify_initial_deposit_visible(page):
    assert page.smartAI('customer_initial_deposit_label_17._**initial_deposit**_label').is_visible()

def enter_initial_deposit(page, value):
    page.smartAI('customer_initial_deposit_input_18._[textbox_under_initial_deposit]_textbox').fill(value)

def click_cancel(page):
    page.smartAI('customer_cancel_action_19._**cancel**_button').click()

def click_add_customer(page):
    page.smartAI('customer_add_customer_action_20._**add_customer**_button').click()

def enter_search_customers(page, value):
    page.smartAI('customer_search`_-_`search_customers..._textbox').fill(value)

def click_add_customer(page):
    page.smartAI('customer_add_customer`_-_`add_customer_button').click()
