from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def setup_driver():
    chrome_options = Options()
    # chrome_options.add_argument("--headless=new")
    service = Service(executable_path='chromedriver.exe')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def parse_page(url):
    driver = setup_driver()
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.search_result_lot_detail.ng-star-inserted')))  # Ожидание основной загрузки

        # Поиск названий автомобилей
        title_elements = driver.find_elements(By.CSS_SELECTOR, '.search_result_lot_detail.ng-star-inserted')
        if title_elements:
            print("\nНайдено автомобилей:", len(title_elements))
            for title_car in title_elements:
                print("Название авто:", title_car.text)

        else:
            print("Названия автомобилей не найдены")

        # Поиск цен (дополненный)
        price_elements = driver.find_elements(By.CSS_SELECTOR, '.desktop-inline.p-ml-2')
        if price_elements:
            print("\nЦены первых 5 лотов:")
            for price in price_elements:
                print("Цена:", price.text)

        # Поиск изображений (дополненный)
        images = driver.find_elements(By.CSS_SELECTOR, 'img[alt="Lot Image"]')
        if images:
            print("\nСсылки на первые 5 изображений:")
            for img in images:
                print(img.get_attribute('src') or img.get_attribute('data-src'))

        # поиск Condition
        condition_elements = driver.find_elements(By.CSS_SELECTOR, '.text-black.p-bold.ng-star-inserted')
        if condition_elements:
            print("\nНайдено Condition:", len(condition_elements))
            for condition_element in condition_elements:
                print("Condition:", condition_element.text)

        else:
            print("Названия Condition")

        # поиск Sale info
        condition_elements = driver.find_elements(By.CSS_SELECTOR, '.search_result_yard_location_label.blue-heading.p-d-flex.p-cursor-pointer.p-bold.ng-star-inserted')
        if condition_elements:
            print("\nНайдено Sale info:", len(condition_elements))
            for condition_element in condition_elements:
                print("Sale info:", condition_element.text)

        else:
            print("Названия Sale info")

        # поиск Lot info
        condition_elements = driver.find_elements(By.CSS_SELECTOR, '.search_result_lot_number.p-bold.blue-heading.ng-star-inserted')
        if condition_elements:
            print("\nНайдено Lot info:", len(condition_elements))
            for condition_element in condition_elements:
                print("Lot info:", condition_element.text)

        else:
            print("Названия Lot info")

    except Exception as e:
        print(f"Ошибка: {str(e)}")
    finally:
        time.sleep(5)
        driver.quit()

if __name__ == "__main__":
    url = "https://www.copart.com/lotSearchResults?free=false&displayStr=AUTOMOBILE,%5B0%20TO%209999999%5D,%5B2019%20TO%202026%5D&from=%2FvehicleFinder&fromSource=widget&qId=de182ddc-661d-46e7-bcb8-e66a669d6990-1741019632491&searchCriteria=%7B%22query%22:%5B%22*%22%5D,%22filter%22:%7B%22YEAR%22:%5B%22lot_year:%5B2019%20TO%202026%5D%22%5D,%22VEHT%22:%5B%22vehicle_type_code:VEHTYPE_V%22%5D,%22FETI%22:%5B%22buy_it_now_code:B1%22%5D,%22TITL%22:%5B%22title_group_code:TITLEGROUP_C%22%5D,%22ODM%22:%5B%22odometer_reading_received:%5B0%20TO%2099400%5D%22%5D%7D,%22searchName%22:%22%22,%22watchListOnly%22:false,%22freeFormSearch%22:false%7D"
    parse_page(url)