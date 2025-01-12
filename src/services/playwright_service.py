import asyncio
import random
import re
from pprint import pprint

from playwright.async_api import async_playwright, Playwright

from src.repository.save_to_db import save_data_to_db
from src.utils.py_logger import get_logger
from src.utils.scroll_page import scroll_to_element
from src.db.session import get_db_context

logger = get_logger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
]


class PlaywrightAsyncRunner:

    def __init__(self, email, password, link, headless=False):
        """
        Ініціалізує об'єкт з необхідними параметрами.
        """
        self.email = email
        self.password = password
        self.link = link
        self.headless = headless
        self.browser = None
        self.page = None
        self.logged_in = False
        self.data = {}

    async def _setup_browser(self, playwright) -> None:
        """
        Налаштовує браузер і сторінку.
        """
        user_agent = random.choice(USER_AGENTS)
        firefox = playwright.firefox

        self.browser = await firefox.launch(headless=self.headless)
        context = await self.browser.new_context(user_agent=user_agent)
        self.page = await context.new_page()

        # Маскування navigator.webdriver
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        await self.page.goto(self.link)

    async def _close_browser(self):
        """
        Закриття браузера
        """
        if self.browser:
            await self.browser.close()

    async def _log_user_agent(self):
        """
        Логування User-Agent браузера.
        """
        user_agent = await self.page.evaluate("navigator.userAgent")
        logger.info(f"User-Agent: {user_agent}", extra={'custom_color': True})

    async def _accept_cookies(self):
        """
        Натискає кнопку "Закрити" cookies, якщо з'являється відповідне вікно.
        """
        try:
            await self.page.wait_for_selector('div.css-e661z2 > button[data-cy="dismiss-cookies-overlay"]')
            await self.page.click('div.css-e661z2 > button[data-cy="dismiss-cookies-overlay"]')
            logger.info(f"Clicked 'Закрити' on the cookie consent.", extra={'custom_color': True})
        except Exception as e:
            logger.warning(f"Failed to click 'Закрити': {e}")

    async def _login(self):
        """
        Авторизація на сайті.
        """
        try:
            if not self.logged_in:
                await asyncio.sleep(random.randint(2, 3))
                await self.page.locator('div.css-zs6l2q > a[data-cy="myolx-link"]').click()

                await asyncio.sleep(4)
                await self.page.locator("input[name='username']").fill(self.email)
                await self.page.locator("input[name='password']").fill(self.password)

                await asyncio.sleep(random.randint(2, 3))
                login_button = await self.page.wait_for_selector('button[data-testid="login-submit-button"]',
                                                                 state='visible')
                await login_button.scroll_into_view_if_needed()
                await login_button.focus()
                await login_button.click()

                logger.info(f"{self.email} ==> Авторизація пройшла успішно!", extra={'custom_color': True})
                self.logged_in = True

                await asyncio.sleep(5)
                await self.page.goto(self.link)

                if self.page.url == self.link:
                    logger.info(f"Успішно перейшли на сторінку: {self.link}", extra={'custom_color': True})
                else:
                    logger.warning(f"Перехід на сторінку {self.link} завершився невдачею.", extra={'custom_color': True})

        except Exception as e:
            logger.error(f"{self.email} | Login failed: {e}")
            raise

    async def scrape_links(self) -> set | None:
        """
        Забирає посилання на товари, 5 перших сторінок.
        """
        try:
            links = set()
            for page_number in range(1, 6):
                url = self.link + f"/uk/list/?page={page_number}"
                logger.info(f"Завантажую сторінку: {url}")

                await self.page.goto(url)
                await self.page.wait_for_selector(
                    "#mainContent > div > div.css-1nvt13t > form > div:nth-child(5) > div > div.css-j0t2x2"
                )
                cards = await self.page.query_selector_all('div[data-cy="l-card"] a.css-qo0cxu')

                for card in cards:
                    href = await card.get_attribute("href")
                    if href:
                        links.add(href)
            logger.info(f"Загальна кількість унікальних посилань: {len(links)}")

            return links

        except Exception as e:
            logger.error(f"Помилка при скрапінгу посилань {e}")
            return None

    async def get_seller(self) -> dict | None:
        try:
            # Витягуємо ім'я продавця
            name_selector = await self.page.query_selector('h4[class="css-1lcz6o7"]')
            if name_selector:
                name = await name_selector.text_content()
                name = name.strip() if name else None
            else:
                name = None

            # Витягуємо рейтинг
            rating_selector = await self.page.query_selector('p[class="css-9pgvpt"]')
            if rating_selector:
                rating = await rating_selector.text_content()
                rating = rating.strip() if rating else None
            else:
                rating = None

            # Витягуємо дату реєстрації продавця
            registered_date_selector = await self.page.query_selector('p[class="css-23d1vy"]')
            if registered_date_selector:
                registered_date = await registered_date_selector.text_content()
                registered_date = registered_date.strip() if registered_date else None
            else:
                registered_date = None

            # Витягуємо дату останньої активності
            last_active_date_selector = await self.page.query_selector('span[class="css-1p85e15"]')
            if last_active_date_selector:
                last_active_date = await last_active_date_selector.text_content()
                last_active_date = last_active_date.strip() if last_active_date else None
            else:
                last_active_date = None

            seller_data = {
                "name": name,
                "rating": rating,
                "registered_date": registered_date,
                "last_active_date": last_active_date,
            }
            self.data['seller'] = {**self.data.get('seller', {}), **seller_data}

            return seller_data

        except Exception as e:
            logger.error(f"Помилка при скрапінгу користувача: {e}")
            return None

    async def get_address(self) -> dict | None:
        """
        Витягує адресу та регіон
        """
        try:
            # Витягуємо адресу
            location_selector = 'p[class="css-1cju8pu"]'
            location_element = await self.page.query_selector(location_selector)
            if location_element:
                location = await location_element.text_content()
                location = location.strip() if location else None
            else:
                location = None

            # Витягуємо регіон
            region_selector = 'div.css-13l8eec p.css-b5m1rv'
            region_element = await self.page.query_selector(region_selector)
            if region_element:
                region = await region_element.text_content()
                region = region.strip() if region else None
            else:
                region = None

            address_data = {"location": location, "region": region}
            self.data['seller'] = {**self.data.get('seller', {}), **address_data}

            return address_data

        except Exception as e:
            logger.error(f"Помилка при скрапінгу адреси: {e}")
            return None

    async def get_product(self) -> dict | None:
        try:
            # Витягуємо дату публікації
            date_selector = 'span[class="css-19yf5ek"]'
            date_element = await self.page.query_selector(date_selector)
            if date_element:
                date_published = await date_element.text_content()
                date_published = date_published.strip() if date_published else None
            else:
                date_published = None

            # Витягуємо назву товару
            title_selector = 'h4[class="css-1kc83jo"]'
            title_element = await self.page.query_selector(title_selector)
            if title_element:
                title = await title_element.text_content()
                title = title.strip() if title else None
            else:
                title = None

            # Витягуємо ціну товару
            price_selector = 'h3[class="css-90xrc0"]'
            price_element = await self.page.query_selector(price_selector)
            if price_element:
                price = await price_element.text_content()
                price = price.strip() if price else None
            else:
                price = None

            # Витягуємо опис товару
            description_selector = 'div[class="css-1o924a9"]'
            description_element = await self.page.query_selector(description_selector)
            if description_element:
                description = await description_element.text_content()
                description = description.strip() if description else None
            else:
                description = None

            # Витягуємо ID товару
            site_id_selector = 'span[class="css-12hdxwj"]'
            site_id_element = await self.page.query_selector(site_id_selector)
            if site_id_element:
                site_id_text = await site_id_element.text_content()
                site_id = re.search(r'\d+', site_id_text).group() if site_id_text else None
            else:
                site_id = None

            # Витягуємо кількість переглядів
            selector = 'span[data-testid="page-view-counter"]'
            views_count_selector = await scroll_to_element(self.page, selector)
            if views_count_selector:
                views_count = await views_count_selector.text_content()
                views_count = re.search(r'\d+', views_count).group() if views_count else None
            else:
                views_count = None

            items = {"date_published": date_published, "title": title, "price": price,
                    "description": description, "site_id": site_id, "views_count": views_count}
            self.data['product'] = {**self.data.get('product', {}), **items}

            return items

        except Exception as e:
            logger.error(f"Помилка при скрапінгу продукту: {e}")
            return None

    async def get_images(self) -> dict | None:
        try:

            # Витягуємо всі зображення
            image_elements = await self.page.query_selector_all('div.swiper-wrapper div.swiper-zoom-container img')
            image_urls = []

            for img in image_elements:
                src = await img.get_attribute('src')
                if src:
                    image_urls.append(src)
                await asyncio.sleep(random.random())
            image_urls = ", ".join(image_urls)

            image = {"images": image_urls}
            self.data['product'] = {**self.data.get('product', {}), **image}

            return image

        except Exception as e:
            logger.error(f"Помилка при скрапінгу картинок: {e}")
            return None

    async def get_info(self) -> dict | None:
        try:
            attributes_selector = 'ul.css-rn93um > li.css-1r0si1e > p.css-b5m1rv'
            delivery_selector = 'ul.css-rn93um > div[data-testid="courier-btn"]'

            attributes = await self.page.query_selector_all(attributes_selector)
            olx_delivery = await self.page.query_selector(delivery_selector)

            info = {}

            if attributes:
                type_item = await attributes[0].text_content()
                type_item = type_item.strip() if type_item else None

                for attribute in attributes[1:]:
                    text = await attribute.text_content()
                    if text and ":" in text:
                        key, value = map(str.strip, text.split(":", 1))
                        info[key] = value
            else:
                type_item = None
            olx_delivery = "YES" if olx_delivery else "NO"

            info = {"type_item": type_item, "info": info, "olx_delivery": olx_delivery}
            self.data['product'] = {**self.data.get('product', {}), **info}

            return info

        except Exception as e:
            logger.error(f"Помилка при скрапінгу info: {e}")
            return None

    async def get_phone(self) -> dict | None:
        """
        Пошук телефону
        """
        try:
            # await self.page.wait_for_selector('button.css-72jcbl', timeout=3000)
            button_phone_selector = await self.page.query_selector('button.css-72jcbl')

            if button_phone_selector:
                await button_phone_selector.click()

                try:
                    phone_selector = await self.page.wait_for_selector('a.css-1dvqodz', timeout=3000)
                    if phone_selector:
                        phone_number = await phone_selector.text_content()
                        phone_number = phone_number.strip() if phone_number else None
                        phone = {"phone_number": phone_number}
                        self.data['seller'] = {**self.data.get('seller', {}), **phone}
                        return phone

                    else:
                        phone = {"phone_number": None}
                        self.data['seller'] = {**self.data.get('seller', {}), **phone}
                        return phone

                except Exception as inner_e:
                    logger.error(f"Помилка при очікуванні телефону: {inner_e}")
                    phone = {"phone_number": None}
                    self.data['seller'] = {**self.data.get('seller', {}), **phone}
                    return phone
            else:
                logger.warning("Не знайдена кнопка для показу телефону.")

        except Exception as e:
            logger.error(f"Помилка при скрапінгу телефону: {e}")

    async def main_get_pages(self, playwright: Playwright):
        """
        Основний метод, для скрапінгу посилань.
        """
        try:
            await self._setup_browser(playwright)
            await self._log_user_agent()
            await self._accept_cookies()
            links = await self.scrape_links()

            return links
        except Exception as e:
            logger.error(f"Error during operation: {e}")
            return None
        finally:
            await self._close_browser()

    async def main_run(self, playwright: Playwright):
        """
        Основний метод, який запускає всі етапи процесу.
        """
        try:
            await self._setup_browser(playwright)
            await asyncio.sleep(random.randint(2, 3))
            await self._log_user_agent()
            await self._accept_cookies()
            await asyncio.sleep(random.randint(2, 3))
            await self._login()
            await self.get_seller()
            await asyncio.sleep(random.randint(2, 3))
            await self.get_address()
            await asyncio.sleep(random.randint(2, 3))
            await self.get_product()
            await self.get_images()
            await self.get_info()
            await asyncio.sleep(random.randint(2, 3))
            await self.get_phone()

            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Error during operation: {e}")


async def playwright_async_run_main(email, password, link):
    runner = PlaywrightAsyncRunner(email, password, link)
    async with async_playwright() as playwright, get_db_context() as db:

        # 1. Для збору посилань на продукти
        product_links = await runner.main_get_pages(playwright)

        # 2. Ітерація для кожного продукту
        if product_links:
            for product_link in list(product_links):
                runner.link = link + product_link
                link_prod = {"link": runner.link}
                runner.data['product'] = {**runner.data.get('product', {}), **link_prod}

                # Зібрати всі дані для продукту
                await runner.main_run(playwright)

                print("********************************************************")
                print(runner.link)
                pprint(runner.data)
                print("********************************************************")

                # Збереження даних у БД
                await save_data_to_db(runner.data, db)


