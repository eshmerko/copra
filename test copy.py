from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import math
import re

def get_total_records(driver):
    try:
        paginator_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.p-paginator-current'))
        )
        paginator_text = paginator_element.text.strip()
        
        # Используем регулярное выражение для поиска общего количества
        match = re.search(r'of\s+([\d,]+)\s+entries', paginator_text)
        if not match:
            raise ValueError("Не найден шаблон количества записей")
            
        total_str = match.group(1).replace(',', '')  # Удаляем запятые в числах
        return int(total_str)
        
    except Exception as e:
        print(f"Ошибка при получении количества записей: {str(e)}")
        print(f"Текст пагинатора: '{paginator_text}'")
        return 0

def setup_driver():
    chrome_options = Options()
    # chrome_options.add_argument("--headless=new")
    service = Service(executable_path='chromedriver.exe')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_total_records(driver):
    try:
        paginator_info = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.p-paginator-current'))
        ).text
        return int(paginator_info.split('of')[-1].split('entries')[0].strip())
    except Exception as e:
        print(f"Ошибка при получении количества записей: {str(e)}")
        return 0

def parse_page(driver):
    data = []
    try:
        # Сбор данных с текущей страницы
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.search_result_lot_detail.ng-star-inserted'))
        )

        # Парсинг данных
        items = driver.find_elements(By.CSS_SELECTOR, '.search_result_lot_detail.ng-star-inserted')
        for item in items:
            try:
                name = item.find_element(By.CSS_SELECTOR, 'a[data-testid="lot-number-link"]').text.strip()
                price = item.find_element(By.CSS_SELECTOR, '.desktop-inline.p-ml-2').text.strip()
                image = item.find_element(By.CSS_SELECTOR, 'img[alt="Lot Image"]').get_attribute('src')
                data.append({'name': name, 'price': price, 'image': image})
            except Exception as e:
                print(f"Ошибка парсинга элемента: {str(e)}")
        
        return data

    except Exception as e:
        print(f"Ошибка при парсинге страницы: {str(e)}")
        return []

def main_parser(url):
    driver = setup_driver()
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.p-paginator-current'))
        )
        
        total_records = get_total_records(driver)
        if total_records == 0:
            return []

        items_per_page = 20
        total_pages = math.ceil(total_records / items_per_page)
        print(f"Всего записей: {total_records}, страниц: {total_pages}")

        all_data = []
        
        for page in range(1, total_pages + 1):
            print(f"\nОбработка страницы {page}/{total_pages}")
            
            # Парсим текущую страницу
            page_data = parse_page(driver)
            all_data.extend(page_data)
            print(f"Собрано записей на странице: {len(page_data)}")

            # Если не последняя страница - переходим дальше
            if page < total_pages:
                try:
                    # Ищем кнопку следующей страницы
                    page_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, f'button.p-paginator-page[aria-label="{page + 1}"]'))
                    )
                    driver.execute_script("arguments[0].scrollIntoView();", page_button)
                    driver.execute_script("arguments[0].click();", page_button)
                    
                    # Ожидание обновления данных
                    WebDriverWait(driver, 15).until(
                        EC.staleness_of(page_button)
                    )
                    time.sleep(2)  # Дополнительная задержка для стабильности
                
                except Exception as e:
                    print(f"Не удалось перейти на страницу {page + 1}: {str(e)}")
                    break

        return all_data

    finally:
        driver.quit()

if __name__ == "__main__":
    url = "https://www.copart.com/lotSearchResults?free=false&displayStr=AUTOMOBILE,%5B0%20TO%209999999%5D,%5B2019%20TO%202026%5D&from=%2FvehicleFinder&fromSource=widget&qId=de182ddc-661d-46e7-bcb8-e66a669d6990-1741019632491&searchCriteria=%7B%22query%22:%5B%22*%22%5D,%22filter%22:%7B%22YEAR%22:%5B%22lot_year:%5B2019%20TO%202026%5D%22%5D,%22VEHT%22:%5B%22vehicle_type_code:VEHTYPE_V%22%5D,%22FETI%22:%5B%22buy_it_now_code:B1%22%5D,%22TITL%22:%5B%22title_group_code:TITLEGROUP_C%22%5D,%22ODM%22:%5B%22odometer_reading_received:%5B0%20TO%2099400%5D%22%5D%7D,%22searchName%22:%22%22,%22watchListOnly%22:false,%22freeFormSearch%22:false%7D"
    result = main_parser(url)
    
    # Вывод результатов
    print("\nИтого собрано записей:", len(result))
    for idx, item in enumerate(result[:3]):  # Показать первые 3 записи
        print(f"\nЗапись {idx + 1}:")
        print(f"Название: {item['name']}")
        print(f"Цена: {item['price']}")
        print(f"Изображение: {item['image']}")