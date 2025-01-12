from src.utils.py_logger import get_logger

logger = get_logger(__name__)


async def scroll_to_element(page, selector):
    """Function for scrolling the page"""
    element = None
    for _ in range(20):
        try:
            element = await page.wait_for_selector(selector, timeout=1000)
            if element:
                # logger.info(f"Element {selector} found with scroll page.", extra={'custom_color': True})
                break
        except Exception as e:
            pass

        await page.mouse.wheel(0, 400)  # Прокрутка вниз на 400
        await page.wait_for_timeout(200)

    return element