import asyncio
import random
import re
import time
from pprint import pprint

from playwright.async_api import async_playwright, Playwright

from src.repository.save_to_db import save_data_to_db
from src.utils.info import USER_AGENTS
from src.utils.py_logger import get_logger
from src.utils.scroll_page import scroll_to_element
from src.db.session import get_db_context

logger = get_logger(__name__)


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
        logger.info(f"User-Agent: {user_agent}")

    async def _accept_cookies(self):
        """
        Натискає кнопку "Закрити" cookies, якщо з'являється відповідне вікно.
        """
        try:
            await self.page.wait_for_selector('div.css-e661z2 > button[data-cy="dismiss-cookies-overlay"]')
            await self.page.click('div.css-e661z2 > button[data-cy="dismiss-cookies-overlay"]')
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
                    logger.info(f"Успішно перейшли на сторінку: {self.link}")
                else:
                    logger.warning(f"Перехід на сторінку {self.link} завершився невдачею.",
                                   extra={'custom_color': True})

        except Exception as e:
            logger.error(f"{self.email} | Login failed: {e}")
            raise

    async def _extract_text(self, selector: str, scroll: bool = False, is_digit: bool = False) -> str | None:
        """
        Витягує текст з елемента за вказаним селектором
        """
        try:
            if scroll:
                element = await scroll_to_element(self.page, selector)
            else:
                element = await self.page.query_selector(selector)

            if not element:
                return None

            text = (await element.text_content()).strip()

            if is_digit:
                match = re.search(r'\d+', text)
                return match.group() if match else None
            return text
        except Exception as e:
            logger.error(f"Error extracting text from selector '{selector}': {e}")
            return None

    async def get_seller(self) -> dict | None:
        """
        Витягує ім'я, рейтинг, дата реєстр, остання дата, адресу та регіон
        """
        try:
            seller_data = {
                'name': await self._extract_text('h4[class="css-1lcz6o7"]'),
                'rating': await self._extract_text('p[class="css-9pgvpt"]'),
                'registered_date': await self._extract_text('p[class="css-23d1vy"]'),
                'last_active_date': await self._extract_text('span[class="css-1p85e15"]'),
                "location": await self._extract_text('p[class="css-1cju8pu"]'),
                "region": await self._extract_text('div.css-13l8eec p.css-b5m1rv')
            }

            self.data['seller'] = {**self.data.get('seller', {}), **seller_data}

            return seller_data

        except Exception as e:
            logger.error(f"Error scraping seller data: {e}")
            return None

    async def get_product(self) -> dict | None:
        """
        Витягує дату публікації, назву, ціну, опис, id, кількість переглядів
        """
        try:
            items = {
                "date_published": await self._extract_text('span[class="css-19yf5ek"]'),
                "title": await self._extract_text('h4[class="css-1kc83jo"]'),
                "price": await self._extract_text('h3[class="css-90xrc0"]'),
                "description": await self._extract_text('div[class="css-1o924a9"]'),
                "site_id": await self._extract_text('span[class="css-12hdxwj"]', is_digit=True),
                "views_count": await self._extract_text('span[data-testid="page-view-counter"]', scroll=True,
                                                        is_digit=True)
            }

            self.data['product'] = {**self.data.get('product', {}), **items}

            return items

        except Exception as e:
            logger.error(f"Помилка при скрапінгу продукту: {e}")
            return None

    async def get_images(self) -> dict | None:
        """
        Витягує всі зображення зі сторінки.
        """
        try:
            image_elements = await self.page.query_selector_all('div.swiper-wrapper div.swiper-zoom-container img')
            image_urls = [
                src for src in await asyncio.gather(*(img.get_attribute('src') for img in image_elements)) if src
            ]

            image_data = {"images": ", ".join(image_urls)}

            self.data['product'] = {**self.data.get('product', {}), **image_data}

            return image_data

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
            button_phone_selector = await self.page.query_selector('button.css-72jcbl')
            if not button_phone_selector:
                logger.warning("Не знайдена кнопка для показу телефону.")
                return None

            await button_phone_selector.click()

            phone_selector = await self.page.wait_for_selector('a.css-1dvqodz', timeout=3000)
            phone_number = None

            if phone_selector:
                phone_number = (await phone_selector.text_content()).strip()

            phone = {"phone_number": phone_number}
            self.data['seller'] = {**self.data.get('seller', {}), **phone}

            return phone

        except Exception as e:
            logger.error(f"Помилка при скрапінгу телефону: {e}")
            return None

    async def scrape_links(self, pages: int = 5) -> set | None:
        """
        Забирає посилання на товари з вказаної кількості сторінок.
        """
        try:
            links = set()
            start_time = time.time()

            for page_number in range(1, pages + 1):
                url = f"{self.link}/uk/list/?page={page_number}"
                await self.page.goto(url)

                try:
                    await self.page.wait_for_selector(
                        "#mainContent > div > div.css-1nvt13t > form > div:nth-child(5) > div > div.css-j0t2x2",
                        timeout=3000
                    )
                except TimeoutError:
                    logger.warning(f"Елементи не знайдено на сторінці: {url}. Пропускаємо.")
                    continue

                cards = await self.page.query_selector_all('div[data-cy="l-card"] a.css-qo0cxu')
                hrefs = await asyncio.gather(*(card.get_attribute("href") for card in cards))

                links.update(filter(None, hrefs))

            logger.info(f"Загальна кількість унікальних посилань: {len(links)}")
            logger.info(f"scrape_links завершено час: {time.time() - start_time:.2f} сек.")

            return links

        except Exception as e:
            logger.error(f"Помилка під час скрапінгу посилань: {e}")
            return None

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
        start_time = time.time()

        try:
            await self._setup_browser(playwright)
            await self._log_user_agent()
            await self._accept_cookies()
            # await self._login()
            logger.info(f"Працює без логінізації на сайті!", extra={'custom_color': True})
            await self.get_seller()
            # await asyncio.sleep(random.randint(2, 3))
            await self.get_product()
            await self.get_images()
            await self.get_info()
            # await asyncio.sleep(random.randint(2, 3))
            await self.get_phone()

            logger.info(f"main_run завершено: {time.time() - start_time:.2f} сек.")

        except Exception as e:
            logger.error(f"Error during operation: {e}")


async def fetch_product_data(email, password, product_link, link, db, semaphore, playwright, success_count):
    async with semaphore:
        runner = None

        try:
            runner = PlaywrightAsyncRunner(email, password, link + product_link)
            link_prod = {"link": runner.link}
            runner.data['product'] = {**runner.data.get('product', {}), **link_prod}

            await runner.main_run(playwright)

            pprint(runner.data)
            await save_data_to_db(runner.data, db)

            success_count[0] += 1

        except Exception as e:
            logger.error(f"Помилка під час обробки продукту {product_link}: {e}", exc_info=True)
        finally:
            await runner.browser.close()


async def playwright_async_run(email, password, link):
    async with async_playwright() as playwright, get_db_context() as db:

        start_time = time.time()

        # 1. Для збору посилань на продукти
        runner = PlaywrightAsyncRunner(email, password, link)
        product_links = await runner.main_get_pages(playwright)

        # 2. Паралельна обробка з обмеженням кількості одночасних запитів
        if product_links:
            semaphore = asyncio.Semaphore(3)
            success_count = [0]
            tasks = [
                fetch_product_data(email, password, product_link, link, db, semaphore, playwright, success_count)
                for product_link in list(product_links)
            ]

            await asyncio.gather(*tasks)

            print("*" * 90)
            logger.info(f"Всього товарів: {len(product_links)}.", extra={'custom_color': True})
            logger.info(f"Записано товарів у базу даних:  {success_count[0]}", extra={'custom_color': True})
            logger.info(f"Загальний час: {time.time() - start_time:.2f} сек.", extra={'custom_color': True})
            print("*" * 90)
