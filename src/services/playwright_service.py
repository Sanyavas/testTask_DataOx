import asyncio
import json
import random
import re

from playwright.async_api import async_playwright, Playwright

from src.utils.py_logger import get_logger
from src.utils.scroll_page import scroll_to_element

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
        logger.info(f"{self.email} | User-Agent: {user_agent}", extra={'custom_color': True})

    async def _accept_cookies(self):
        """
        Натискає кнопку "Закрити" cookies, якщо з'являється відповідне вікно.
        """
        try:
            await self.page.wait_for_selector('div.css-e661z2 > button[data-cy="dismiss-cookies-overlay"]')
            await self.page.click('div.css-e661z2 > button[data-cy="dismiss-cookies-overlay"]')
            logger.info(f"{self.email} | Clicked 'Закрити' on the cookie consent.", extra={'custom_color': True})
        except Exception as e:
            logger.warning(f"{self.email} | Failed to click 'Закрити': {e}")

    async def _login(self):
        """
        Авторизація на сайті.
        """
        try:
            await asyncio.sleep(random.randint(2, 3))
            await self.page.locator('div.css-zs6l2q > a[data-cy="myolx-link"]').click()
            logger.info("Перехід на сторінку логіна успішний!", extra={'custom_color': True})

            # await self.page.slow_mo(50)
            await asyncio.sleep(random.randint(2, 3))
            await self.page.locator("input[name='username']").fill(self.email)
            await self.page.locator("input[name='password']").fill(self.password)

            await asyncio.sleep(random.randint(2, 3))
            login_button = await self.page.wait_for_selector('button[data-testid="login-submit-button"]',
                                                             state='visible')
            await login_button.scroll_into_view_if_needed()
            await login_button.focus()
            await login_button.click()
            logger.info(f"{self.email} ==> Авторизація пройшла успішно!", extra={'custom_color': True})

            await asyncio.sleep(8)
            await self.page.goto(self.link)

            if self.page.url == self.link:
                logger.info(f"Успішно перейшли на сторінку: {self.link}", extra={'custom_color': True})
            else:
                logger.warning(f"Перехід на сторінку {self.link} завершився невдачею.", extra={'custom_color': True})

        except Exception as e:
            logger.error(f"{self.email} | Login failed: {e}")
            raise

    async def get_seller(self):
        try:
            # Витягуємо ім'я продавця
            name_selector = 'h4[class="css-1lcz6o7"]'
            name_seller = await self.page.text_content(name_selector)
            name_seller = name_seller.strip() if name_seller else None
            print(f"{name_seller=}")

            # Витягуємо рейтинг
            rating_selector = await self.page.query_selector('p[class="css-9pgvpt"]')
            if rating_selector:
                rating = await rating_selector.text_content()
                rating = rating.strip() if rating else None
                print(f"{rating=}")

            # Витягуємо дату реєстрації продавця
            registered_date_selector = 'p[class="css-23d1vy"]'
            registered_date = await self.page.text_content(registered_date_selector)
            registered_date = registered_date.strip() if registered_date else None
            print(f"{registered_date=}")

            # Витягуємо дату реєстрації користувача
            last_active_date_selector = 'span[class="css-1p85e15"]'
            last_active_date = await self.page.text_content(last_active_date_selector)
            last_active_date = last_active_date.strip() if last_active_date else None
            print(f"{last_active_date=}")

            return {"name_seller": name_seller, "rating": rating, "registered_date": registered_date,
                    "last_active_date": last_active_date}
        except Exception as e:
            logger.error(f"Помилка при скрапінгу користувача {e}")
            return None

    async def get_address(self):
        """
        Витягує адресу та регіон
        """
        try:
            location_selector = 'p[class="css-1cju8pu"]'
            location = await self.page.text_content(location_selector)
            location = location.strip() if location else None
            print(f"{location=}")

            region_selector = 'div.css-13l8eec p.css-b5m1rv'
            region = await self.page.text_content(region_selector)
            region = region.strip() if region else None
            print(f"{region=}")

            return {"location": location, "region": region}

        except Exception as e:
            logger.error(f"Помилка при скрапінгу адреси: {e}")
            return None

    async def get_product(self):
        try:
            # Витягуємо дату публікації
            date_selector = 'span[class="css-19yf5ek"]'
            date_published = await self.page.text_content(date_selector)
            date_published = date_published.strip() if date_published else None
            print(f"{date_published=}")

            # Витягуємо назву товару
            title_selector = 'h4[class="css-1kc83jo"]'
            title = await self.page.text_content(title_selector)
            title = title.strip() if title else None
            print(f"{title=}")

            # Витягуємо ціну товару
            price_selector = 'h3[class="css-90xrc0"]'
            price = await self.page.text_content(price_selector)
            # price = re.search(r'\d+', price).group() if price else None
            price = price.strip() if price else None
            print(f"{price=} {type(price)}")

            # Витягуємо опис товару
            description_selector = 'div[class="css-1o924a9"]'
            description = await self.page.text_content(description_selector)
            description = description.strip() if description else None
            print(f"{description=}")

            # Витягуємо ID товару
            site_id_selector = 'span[class="css-12hdxwj"]'
            site_id = await self.page.text_content(site_id_selector)
            site_id = re.search(r'\d+', site_id).group() if site_id else None
            # site_id = site_id.strip() if site_id else None
            print(f"{site_id=}")

            # Витягуємо кількість переглядів
            selector = 'span[data-testid="page-view-counter"]'
            views_count_selector = await scroll_to_element(self.page, selector)
            if views_count_selector:
                views_count = await views_count_selector.text_content()
                views_count = re.search(r'\d+', views_count).group() if views_count else None
                # views_count = views_count.strip() if views_count else None
                print(f"{views_count=}")

            return {"date_published": date_published, "title": title, "price": price,
                    "description": description, "site_id": site_id, "views_count": views_count}

        except Exception as e:
            logger.error(f"Помилка при скрапінгу продукту: {e}")
            return None

    async def get_images(self):
        try:

            # Витягуємо всі зображення
            image_elements = await self.page.query_selector_all('div.swiper-wrapper div.swiper-zoom-container img')
            image_urls = []

            for img in image_elements:
                src = await img.get_attribute('src')
                if src:
                    image_urls.append(src)
                await asyncio.sleep(random.random())
            print(f"{image_urls=}")

            return {"images": image_urls}

        except Exception as e:
            logger.error(f"Помилка при скрапінгу картинок: {e}")
            return None


    async def get_info(self):
        try:
            attributes_selector = 'ul.css-rn93um > li.css-1r0si1e > p.css-b5m1rv'
            delivery_selector = 'ul.css-rn93um > div[data-testid="courier-btn"]'

            attributes = await self.page.query_selector_all(attributes_selector)
            delivery = await self.page.query_selector(delivery_selector)

            result = {}

            if attributes:
                type_item = await attributes[0].text_content()
                type_item = type_item.strip() if type_item else None
                result["type_item"] = type_item
                print(f"{type_item=}")

                for attribute in attributes[1:]:
                    text = await attribute.text_content()
                    if text and ":" in text:
                        key, value = map(str.strip, text.split(":", 1))
                        result[key] = value

            result["delivery"] = True if delivery else False
            print(f"{result=}")

            return result

        except Exception as e:
            logger.error(f"Помилка при скрапінгу info: {e}")
            return None

    async def get_phone(self):
        """
        Пошук телефону на сайті.
        """
        try:
            await self.page.wait_for_selector('button.css-72jcbl', timeout=5000)
            button_phone_selector = await self.page.query_selector('button.css-72jcbl')

            if button_phone_selector:
                await button_phone_selector.click()
                phone_selector = await self.page.wait_for_selector('a.css-1dvqodz', timeout=3000)

                if phone_selector:
                    phone_number = await phone_selector.text_content()
                    phone_number = phone_number.strip() if phone_number else None
                    print(f"phone: {phone_number}")

                    return {"phone_number": phone_number}
                else:
                    return {"phone_number": None}
            else:
                return {"phone_number": None}

        except Exception as e:
            logger.error(f"Помилка при скрапінгу телефону: {e}")
            return None


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
            # await self._login()
            await self.get_seller()
            await asyncio.sleep(random.randint(2, 3))
            await self.get_address()
            await asyncio.sleep(random.randint(2, 3))
            await self.get_product()
            await self.get_images()
            await self.get_info()
            await asyncio.sleep(random.randint(2, 3))
            await self.get_phone()

            await asyncio.sleep(25)

        except Exception as e:
            logger.error(f"{self.email} | Error during operation: {e}")
        finally:
            await self._close_browser()


async def playwright_async_run(email, password, link):
    """
    Головна функція для запуску операцій.
    """
    runner = PlaywrightAsyncRunner(email, password, link)
    async with async_playwright() as playwright:
        await runner.main_run(playwright)
