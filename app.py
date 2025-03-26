import time
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

import telebot
from telebot import apihelper

class CopartParser:
    def __init__(self, bot_token: str, chat_id: str, db_path: str = 'copart_lots.db'):
        # Настройка ChromeOptions
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920x1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Инициализация драйвера
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        self.driver.implicitly_wait(10)

        # Инициализация телеграм бота
        self.bot = telebot.TeleBot(bot_token)
        self.chat_id = chat_id
        
        # Настройка базы данных
        self.db_path = db_path
        self._init_db()
        
        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('parser.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _init_db(self) -> None:
        """Инициализация структуры базы данных"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица лотов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS lots (
                    lot_id TEXT PRIMARY KEY,
                    link TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    title TEXT,
                    dealer TEXT,
                    price REAL,
                    image_urls TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # Таблица истории цен
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lot_id TEXT NOT NULL,
                    price REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(lot_id) REFERENCES lots(lot_id)
                )
            ''')
            
            conn.commit()

    def parse_page(self, url: str, page_number: int = 1) -> List[Dict]:
        """Парсинг страницы с лотами"""
        self.logger.info(f"Начинаем парсинг страницы {page_number}")
        
        try:
            paginated_url = f"{url}&page={page_number}"
            self.driver.get(paginated_url)
            
            # Ожидание загрузки контента
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.search_result_lot_detail_block')))
            
            lot_blocks = self.driver.find_elements(By.CSS_SELECTOR, '.search_result_lot_detail_block')
            self.logger.info(f"Найдено {len(lot_blocks)} лотов на странице {page_number}")
            
            parsed_lots = []
            for index, lot_block in enumerate(lot_blocks):
                try:
                    lot_data = {
                        'lot_id': self._get_lot_id(lot_block),
                        'name': self._get_lot_name(lot_block),
                        'price': self._get_lot_price(lot_block),
                        'link': self._get_lot_link(lot_block),
                        'title': self._get_lot_title(lot_block),
                        'dealer': self._get_lot_dealer(lot_block),
                        'images': self._get_lot_images(lot_block)
                    }
                    parsed_lots.append(lot_data)
                    self.logger.debug(f"Обработан лот {index + 1}/{len(lot_blocks)}")
                except Exception as e:
                    self.logger.error(f"Ошибка обработки лота: {str(e)}")
            
            return parsed_lots
        
        except TimeoutException:
            self.logger.warning(f"Таймаут при загрузке страницы {page_number}")
            return []
        except Exception as e:
            self.logger.error(f"Критическая ошибка при парсинге: {str(e)}")
            return []

    def _get_lot_id(self, element) -> str:
        """Извлечение ID лота"""
        try:
            link_element = element.find_element(By.CSS_SELECTOR, 'a[href*="/lot/"]')
            href = link_element.get_attribute('href')
            return href.split('/lot/')[-1].split('/')[0]
        except NoSuchElementException:
            return 'unknown_id'

    def _get_lot_name(self, element) -> str:
        """Извлечение названия лота"""
        try:
            return element.find_element(By.CSS_SELECTOR, '.lot-name').text.strip()
        except NoSuchElementException:
            return 'Название не указано'

    def _get_lot_price(self, element) -> float:
        """Извлечение цены лота"""
        try:
            price_text = element.find_element(By.CSS_SELECTOR, '.currencyAmount').text
            return float(price_text.replace('$', '').replace(',', ''))
        except (NoSuchElementException, ValueError):
            return 0.0

    def _get_lot_link(self, element) -> str:
        """Извлечение ссылки на лот"""
        try:
            path = element.find_element(By.CSS_SELECTOR, 'a[href*="/lot/"]').get_attribute('href')
            return f"https://www.copart.com{path}" if not path.startswith('http') else path
        except NoSuchElementException:
            return 'Ссылка недоступна'

    def _get_lot_title(self, element) -> str:
        """Извлечение информации о сертификате"""
        try:
            return element.find_element(By.XPATH, './/span[contains(@title, "CERTIFICATE OF TITLE")]').text.strip()
        except NoSuchElementException:
            return 'Сертификат отсутствует'

    def _get_lot_dealer(self, element) -> str:
        """Извлечение информации о дилере"""
        try:
            return element.find_element(By.CSS_SELECTOR, '.dealer-info').text.strip()
        except NoSuchElementException:
            return 'Дилер не указан'

    def _get_lot_images(self, element) -> List[str]:
        """Извлечение изображений лота"""
        try:
            images = element.find_elements(By.CSS_SELECTOR, 'img.lot-image')
            return [img.get_attribute('src') for img in images if img.get_attribute('src')]
        except NoSuchElementException:
            return []

    def sync_lots(self, base_url: str, max_pages: int = 3) -> None:
        """Основной метод синхронизации данных"""
        self.logger.info("Начало синхронизации данных")
        
        all_lots = []
        for page in range(1, max_pages + 1):
            page_lots = self.parse_page(base_url, page)
            all_lots.extend(page_lots)
            time.sleep(2)  # Задержка между запросами

        self._save_to_db(all_lots)
        self._check_for_changes(all_lots)
        self.logger.info(f"Синхронизация завершена. Обработано {len(all_lots)} лотов")

    def _save_to_db(self, lots: List[Dict]) -> None:
        """Сохранение данных в базу"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for lot in lots:
                try:
                    # Вставка или обновление лота
                    cursor.execute('''
                        INSERT INTO lots 
                        (lot_id, link, name, title, dealer, price, image_urls, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(lot_id) DO UPDATE SET
                            price = excluded.price,
                            updated_at = excluded.updated_at
                    ''', (
                        lot['lot_id'],
                        lot['link'],
                        lot['name'],
                        lot['title'],
                        lot['dealer'],
                        lot['price'],
                        ','.join(lot['images'])
                    ))
                    
                    # Запись истории цен
                    cursor.execute('''
                        INSERT INTO price_history (lot_id, price)
                        VALUES (?, ?)
                    ''', (lot['lot_id'], lot['price']))
                    
                except sqlite3.Error as e:
                    self.logger.error(f"Ошибка БД для лота {lot['lot_id']}: {str(e)}")
            
            conn.commit()

    def _check_for_changes(self, new_lots: List[Dict]) -> None:
        """Проверка изменений и отправка уведомлений"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for lot in new_lots:
                cursor.execute('''
                    SELECT price FROM lots 
                    WHERE lot_id = ? 
                    ORDER BY updated_at DESC 
                    LIMIT 1
                ''', (lot['lot_id'],))
                
                previous_price = cursor.fetchone()
                if previous_price and previous_price[0] != lot['price']:
                    message = (
                        f"🚨 Изменение цены!\n"
                        f"Лот: {lot['name']}\n"
                        f"Старая цена: ${previous_price[0]:,.2f}\n"
                        f"Новая цена: ${lot['price']:,.2f}\n"
                        f"Ссылка: {lot['link']}"
                    )
                    self._send_notification(message)

    def _send_notification(self, message: str) -> None:
        """Отправка уведомления в Telegram"""
        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                disable_web_page_preview=True
            )
            self.logger.info("Уведомление отправлено")
        except Exception as e:
            self.logger.error(f"Ошибка отправки сообщения: {str(e)}")

    def __del__(self):
        """Завершение работы драйвера"""
        if hasattr(self, 'driver'):
            self.driver.quit()
            self.logger.info("Браузер закрыт")

def main():
    # Конфигурация
    BOT_TOKEN = '7112012938:AAFZX_D2EqQUaOuybR17jEJQ7btnOYCjnRA'
    CHAT_ID = '-1002147359725'
    BASE_URL = ('https://www.copart.com/lotSearchResults?free=false&displayStr=AUTOMOBILE,%5B0%20TO%209999999%5D,%5B2019%20TO%202026%5D&from=%2FvehicleFinder&fromSource=widget&qId=de182ddc-661d-46e7-bcb8-e66a669d6990-1741019632491&searchCriteria=%7B%22query%22:%5B%22*%22%5D,%22filter%22:%7B%22YEAR%22:%5B%22lot_year:%5B2019%20TO%202026%5D%22%5D,%22VEHT%22:%5B%22vehicle_type_code:VEHTYPE_V%22%5D,%22FETI%22:%5B%22buy_it_now_code:B1%22%5D,%22TITL%22:%5B%22title_group_code:TITLEGROUP_C%22%5D,%22ODM%22:%5B%22odometer_reading_received:%5B0%20TO%2099400%5D%22%5D%7D,%22searchName%22:%22%22,%22watchListOnly%22:false,%22freeFormSearch%22:false%7D')
    
    # Инициализация парсера
    parser = CopartParser(
        bot_token=BOT_TOKEN,
        chat_id=CHAT_ID,
        db_path='copart.db'
    )
    
    try:
        # Запуск синхронизации
        parser.sync_lots(
            base_url=BASE_URL,
            max_pages=2
        )
    except KeyboardInterrupt:
        parser.logger.warning("Прервано пользователем")
    except Exception as e:
        parser.logger.error(f"Критическая ошибка: {str(e)}")
    finally:
        if parser.driver:
            parser.driver.quit()

if __name__ == '__main__':
    main()