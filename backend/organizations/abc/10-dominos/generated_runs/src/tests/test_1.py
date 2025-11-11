from playwright.sync_api import sync_playwright

import json

from pathlib import Path

from lib.smart_ai import patch_page_with_smartai

from pages.dominos_add_address_page_methods import *

from pages.dominos_add_page_methods import *

from pages.dominos_enter_address_page_methods import *

from pages.dominos_login_page_methods import *

from pages.dominos_main_page_methods import *

from pages.dominos_pizza_page_methods import *

from pages.dominos_viewcart_page_methods import *

def test_positive_order_flow(page):
    page.goto("https://www.dominos.co.in/")
    click_order_online_now(page)
    click_menu(page)
    click_add(page)
    click_view_cart(page)
    click_add_address(page)
    enter_building_house_flat_floor_no(page, "19 hoodi")
    assert_enter_building_house_flat_floor_no(page, "19 hoodi")
    enter_address(page, "Bangalore")
    assert_enter_address(page, "Bangalore")
    enter_your_name(page, "Manoj")
    assert_enter_your_name(page, "Manoj")
    enter_your_contact_number(page, "1234567890")
    assert_enter_your_contact_number(page, "1234567890")
    click_save_address(page)

def test_negative_order_flow(page):
    page.goto("https://www.dominos.co.in/")
    click_order_online_now(page)
    click_menu(page)
    click_add(page)
    click_view_cart(page)
    click_add_address(page)
    enter_building_house_flat_floor_no(page, "")
    assert_enter_building_house_flat_floor_no(page, "")
    enter_address(page, "")
    assert_enter_address(page, "")
    enter_your_name(page, "")
    assert_enter_your_name(page, "")
    enter_your_contact_number(page, "")
    assert_enter_your_contact_number(page, "")
    click_save_address(page)

def test_edge_order_flow(page):
    page.goto("https://www.dominos.co.in/")
    click_order_online_now(page)
    click_menu(page)
    click_add(page)
    click_view_cart(page)
    click_add_address(page)
    enter_building_house_flat_floor_no(page, "19 hoodi" * 50)
    assert_enter_building_house_flat_floor_no(page, "19 hoodi" * 50)
    enter_address(page, "Bangalore" * 50)
    assert_enter_address(page, "Bangalore" * 50)
    enter_your_name(page, "Manoj" * 50)
    assert_enter_your_name(page, "Manoj" * 50)
    enter_your_contact_number(page, "1234567890" * 5)
    assert_enter_your_contact_number(page, "1234567890" * 5)
    click_save_address(page)