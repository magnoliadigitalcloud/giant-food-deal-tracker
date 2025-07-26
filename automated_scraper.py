#!/usr/bin/env python3
"""
Automated Giant Food Deal Scraper
Automatically finds items with both digital coupons AND sales
Sends email notifications when great deals are found
"""

import requests
import json
import time
import smtplib
import schedule
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Deal:
    product_name: str
    original_price: float
    sale_price: float
    coupon_discount: float
    final_price: float
    savings: float
    savings_percent: float
    coupon_description: str
    sale_description: str
    expiry_date: str
    product_url: str
    image_url: str

class GiantFoodAutomatedScraper:
    def __init__(self, config_file: str = "scraper_config.json"):
        self.config = self.load_config(config_file)
        self.session = requests.Session()
        self.setup_session()
        self.deals_database = "automated_deals.json"
        self.previous_deals = self.load_previous_deals()
        
    def load_config(self, config_file: str) -> Dict:
        """Load configuration or create default"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self.create_default_config(config_file)
    
    def create_default_config(self, config_file: str) -> Dict:
        """Create default configuration file"""
        config = {
            "giant_food": {
                "base_url": "https://giantfood.com",
                "store_id": "0774",  # Bowie, MD area
                "zip_code": "20715",
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
            },
            "scraping": {
                "delay_between_requests": 2,
                "timeout": 30,
                "retry_attempts": 3,
                "use_browser": True,  # Use Selenium for JavaScript-heavy pages
                "headless": True     # Run browser in background
            },
            "filters": {
                "minimum_savings_dollar": 1.50,
                "minimum_savings_percent": 25,
                "max_original_price": 100.00,
                "categories_to_track": ["all"],  # or specific: ["dairy", "produce", "meat"]
                "exclude_categories": ["alcohol", "tobacco"]
            },
            "notifications": {
                "email": {
                    "enabled": True,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "sender_email": "your_email@gmail.com",
                    "sender_password": "your_app_password",
                    "recipient_email": "your_email@gmail.com",
                    "send_summary": True,
                    "send_individual_deals": False
                }
            },
            "schedule": {
                "enabled": True,
                "check_times": ["08:00", "18:00"],  # 8 AM and 6 PM
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"Created default config: {config_file}")
        print("⚠️  Please update with your email settings before running!")
        return config
    
    def setup_session(self):
        """Configure requests session with proper headers"""
        self.session.headers.update({
            'User-Agent': self.config['giant_food']['user_agent'],
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        })
    
    def setup_browser(self) -> webdriver.Chrome:
        """Setup Selenium browser for JavaScript-heavy pages"""
        options = Options()
        
        if self.config['scraping']['headless']:
            options.add_argument('--headless')
        
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f"--user-agent={self.config['giant_food']['user_agent']}")
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def load_previous_deals(self) -> List[Dict]:
        """Load previously found deals to avoid duplicates"""
        try:
            with open(self.deals_database, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def save_deals(self, deals: List[Deal]):
        """Save deals to database"""
        deal_dicts = []
        for deal in deals:
            deal_dict = {
                'product_name': deal.product_name,
                'original_price': deal.original_price,
                'sale_price': deal.sale_price,
                'coupon_discount': deal.coupon_discount,
                'final_price': deal.final_price,
                'savings': deal.savings,
                'savings_percent': deal.savings_percent,
                'coupon_description': deal.coupon_description,
                'sale_description': deal.sale_description,
                'expiry_date': deal.expiry_date,
                'product_url': deal.product_url,
                'image_url': deal.image_url,
                'found_date': datetime.now().isoformat()
            }
            deal_dicts.append(deal_dict)
        
        with open(self.deals_database, 'w') as f:
            json.dump(deal_dicts, f, indent=2)
    
    def scrape_digital_coupons(self) -> Dict[str, Dict]:
        """Scrape digital coupons using browser automation"""
        logger.info("Scraping digital coupons...")
        
        if not self.config['scraping']['use_browser']:
            return self.scrape_coupons_api()
            
        driver = self.setup_browser()
        coupons = {}
        
        try:
            # Navigate to digital coupons page
            coupons_url = f"{self.config['giant_food']['base_url']}/coupons-weekly-circular/digital-coupons"
            driver.get(coupons_url)
            
            # Wait for page to load
            WebDriverWait(driver, self.config['scraping']['timeout']).until(
                EC.presence_of_element_located((By.CLASS_NAME, "coupon-card"))
            )
            
            # Find all coupon elements
            coupon_elements = driver.find_elements(By.CSS_SELECTOR, "[data-testid='coupon-card'], .coupon-card, .coupon-item")
            
            logger.info(f"Found {len(coupon_elements)} coupon elements")
            
            for element in coupon_elements:
                try:
                    coupon_data = self.extract_coupon_data(element)
                    if coupon_data:
                        product_key = self.normalize_product_name(coupon_data['product_name'])
                        coupons[product_key] = coupon_data
                        
                except Exception as e:
                    logger.warning(f"Error extracting coupon: {e}")
                    continue
            
        except TimeoutException:
            logger.error("Timeout waiting for coupons page to load")
        except Exception as e:
            logger.error(f"Error scraping coupons: {e}")
        finally:
            driver.quit()
        
        logger.info(f"Successfully scraped {len(coupons)} digital coupons")
        return coupons
    
    def extract_coupon_data(self, element) -> Optional[Dict]:
        """Extract coupon data from a web element"""
        try:
            # Try different selectors for product name
            product_name = None
            for selector in ['.product-name', '.coupon-title', 'h3', 'h4', '[data-testid="product-name"]']:
                try:
                    product_name = element.find_element(By.CSS_SELECTOR, selector).text.strip()
                    if product_name:
                        break
                except NoSuchElementException:
                    continue
            
            if not product_name:
                return None
            
            # Try to find discount amount
            discount_text = None
            for selector in ['.discount-amount', '.coupon-value', '.savings', '[data-testid="discount"]']:
                try:
                    discount_text = element.find_element(By.CSS_SELECTOR, selector).text.strip()
                    if discount_text:
                        break
                except NoSuchElementException:
                    continue
            
            if not discount_text:
                return None
            
            # Extract numeric discount value
            discount_match = re.search(r'\$?(\d+\.?\d*)', discount_text)
            if not discount_match:
                return None
            
            discount_amount = float(discount_match.group(1))
            
            # Try to find expiry date
            expiry_date = "Unknown"
            for selector in ['.expiry-date', '.expires', '.valid-until']:
                try:
                    expiry_text = element.find_element(By.CSS_SELECTOR, selector).text.strip()
                    if expiry_text:
                        expiry_date = expiry_text
                        break
                except NoSuchElementException:
                    continue
            
            # Try to find qualifying products/description
            description = discount_text
            for selector in ['.coupon-description', '.qualifying-products', '.details']:
                try:
                    desc_text = element.find_element(By.CSS_SELECTOR, selector).text.strip()
                    if desc_text:
                        description = desc_text
                        break
                except NoSuchElementException:
                    continue
            
            return {
                'product_name': product_name,
                'discount_amount': discount_amount,
                'description': description,
                'expiry_date': expiry_date,
                'coupon_text': discount_text
            }
            
        except Exception as e:
            logger.warning(f"Error extracting coupon data: {e}")
            return None
    
    def scrape_weekly_sales(self) -> Dict[str, Dict]:
        """Scrape weekly sales/circular"""
        logger.info("Scraping weekly sales...")
        
        driver = self.setup_browser()
        sales = {}
        
        try:
            # Navigate to weekly ad
            sales_url = f"{self.config['giant_food']['base_url']}/coupons-weekly-circular/weekly-ad"
            driver.get(sales_url)
            
            # Wait for page to load
            WebDriverWait(driver, self.config['scraping']['timeout']).until(
                EC.presence_of_element_located((By.CLASS_NAME, "sale-item"))
            )
            
            # Find all sale elements
            sale_elements = driver.find_elements(By.CSS_SELECTOR, "[data-testid='sale-item'], .sale-item, .product-card")
            
            logger.info(f"Found {len(sale_elements)} sale elements")
            
            for element in sale_elements:
                try:
                    sale_data = self.extract_sale_data(element)
                    if sale_data:
                        product_key = self.normalize_product_name(sale_data['product_name'])
                        sales[product_key] = sale_data
                        
                except Exception as e:
                    logger.warning(f"Error extracting sale: {e}")
                    continue
                    
        except TimeoutException:
            logger.error("Timeout waiting for sales page to load")
        except Exception as e:
            logger.error(f"Error scraping sales: {e}")
        finally:
            driver.quit()
        
        logger.info(f"Successfully scraped {len(sales)} sale items")
        return sales
    
    def extract_sale_data(self, element) -> Optional[Dict]:
        """Extract sale data from a web element"""
        try:
            # Product name
            product_name = None
            for selector in ['.product-name', '.item-name', 'h3', 'h4', '[data-testid="product-name"]']:
                try:
                    product_name = element.find_element(By.CSS_SELECTOR, selector).text.strip()
                    if product_name:
                        break
                except NoSuchElementException:
                    continue
            
            if not product_name:
                return None
            
            # Sale price
            sale_price = None
            for selector in ['.sale-price', '.current-price', '.price-now', '[data-testid="sale-price"]']:
                try:
                    price_text = element.find_element(By.CSS_SELECTOR, selector).text.strip()
                    price_match = re.search(r'\$?(\d+\.?\d*)', price_text)
                    if price_match:
                        sale_price = float(price_match.group(1))
                        break
                except (NoSuchElementException, ValueError):
                    continue
            
            # Original price
            original_price = sale_price  # Default to sale price if no original found
            for selector in ['.original-price', '.was-price', '.price-was', '[data-testid="original-price"]']:
                try:
                    price_text = element.find_element(By.CSS_SELECTOR, selector).text.strip()
                    price_match = re.search(r'\$?(\d+\.?\d*)', price_text)
                    if price_match:
                        original_price = float(price_match.group(1))
                        break
                except (NoSuchElementException, ValueError):
                    continue
            
            if not sale_price:
                return None
            
            # Sale description
            sale_description = f"On sale for ${sale_price:.2f}"
            for selector in ['.sale-description', '.promo-text', '.deal-text']:
                try:
                    desc_text = element.find_element(By.CSS_SELECTOR, selector).text.strip()
                    if desc_text:
                        sale_description = desc_text
                        break
                except NoSuchElementException:
                    continue
            
            return {
                'product_name': product_name,
                'original_price': original_price,
                'sale_price': sale_price,
                'sale_description': sale_description
            }
            
        except Exception as e:
            logger.warning(f"Error extracting sale data: {e}")
            return None
    
    def normalize_product_name(self, name: str) -> str:
        """Normalize product name for matching"""
        # Remove brand variations, sizes, etc. for better matching
        normalized = re.sub(r'\b\d+(\.\d+)?\s*(oz|lb|ct|fl oz|ml|l)\b', '', name.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def find_double_deals(self, coupons: Dict, sales: Dict) -> List[Deal]:
        """Find products that have both coupons and sales"""
        deals = []
        
        logger.info(f"Matching {len(coupons)} coupons with {len(sales)} sales...")
        
        for coupon_key, coupon_data in coupons.items():
            for sale_key, sale_data in sales.items():
                # Check if products match (fuzzy matching)
                if self.products_match(coupon_key, sale_key, coupon_data, sale_data):
                    deal = self.create_deal_object(coupon_data, sale_data)
                    
                    if self.deal_meets_criteria(deal):
                        deals.append(deal)
                        logger.info(f"Found deal: {deal.product_name} - Save ${deal.savings:.2f}")
        
        # Sort by savings amount (highest first)
        deals.sort(key=lambda x: x.savings, reverse=True)
        
        logger.info(f"Found {len(deals)} double-savings deals")
        return deals
    
    def products_match(self, coupon_key: str, sale_key: str, coupon_data: Dict, sale_data: Dict) -> bool:
        """Determine if coupon and sale are for the same product"""
        # Direct key match
        if coupon_key == sale_key:
            return True
        
        # Fuzzy matching - check if one contains the other
        if coupon_key in sale_key or sale_key in coupon_key:
            return True
        
        # Check brand names and key terms
        coupon_words = set(coupon_key.split())
        sale_words = set(sale_key.split())
        
        # If they share significant words, consider it a match
        common_words = coupon_words.intersection(sale_words)
        if len(common_words) >= 2:  # At least 2 words in common
            return True
        
        return False
    
    def create_deal_object(self, coupon_data: Dict, sale_data: Dict) -> Deal:
        """Create a Deal object from coupon and sale data"""
        original_price = sale_data['original_price']
        sale_price = sale_data['sale_price']
        coupon_discount = coupon_data['discount_amount']
        
        final_price = max(0, sale_price - coupon_discount)
        savings = original_price - final_price
        savings_percent = (savings / original_price * 100) if original_price > 0 else 0
        
        return Deal(
            product_name=sale_data['product_name'],
            original_price=original_price,
            sale_price=sale_price,
            coupon_discount=coupon_discount,
            final_price=final_price,
            savings=savings,
            savings_percent=savings_percent,
            coupon_description=coupon_data['description'],
            sale_description=sale_data['sale_description'],
            expiry_date=coupon_data.get('expiry_date', 'Unknown'),
            product_url='',
            image_url=''
        )
    
    def deal_meets_criteria(self, deal: Deal) -> bool:
        """Check if deal meets configured criteria"""
        filters = self.config['filters']
        
        # Minimum savings checks
        if deal.savings < filters['minimum_savings_dollar']:
            return False
        
        if deal.savings_percent < filters['minimum_savings_percent']:
            return False
        
        # Maximum price check
        if deal.original_price > filters['max_original_price']:
            return False
        
        return True
    
    def send_email_notification(self, deals: List[Deal]):
        """Send email notification with found deals"""
        if not self.config['notifications']['email']['enabled']:
            return
        
        if not deals:
            logger.info("No deals to email")
            return
        
        try:
            email_config = self.config['notifications']['email']
            
            # Create email content
            subject = f"🛍️ {len(deals)} Giant Food Double-Savings Deals Found!"
            
            html_body = self.create_email_html(deals)
            text_body = self.create_email_text(deals)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = email_config['sender_email']
            msg['To'] = email_config['recipient_email']
            
            # Add both plain text and HTML versions
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['sender_email'], email_config['sender_password'])
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent successfully with {len(deals)} deals")
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
    
    def create_email_html(self, deals: List[Deal]) -> str:
        """Create HTML email content"""
        total_savings = sum(deal.savings for deal in deals)
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #e31837;">🛍️ Giant Food Double-Savings Alert!</h1>
            <p style="font-size: 18px; color: #333;">
                Found <strong>{len(deals)} deals</strong> with both sales AND digital coupons!<br>
                💰 Total potential savings: <strong>${total_savings:.2f}</strong>
            </p>
            
            <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; font-size: 14px; color: #666;">
                    ✅ These items are on sale AND have digital coupons<br>
                    📱 Make sure to clip the coupons in your Giant Food app<br>
                    ⏰ Check expiration dates before shopping
                </p>
            </div>
        """
        
        for i, deal in enumerate(deals, 1):
            html += f"""
            <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px;">
                <h3 style="color: #e31837; margin: 0 0 10px 0;">{i}. {deal.product_name}</h3>
                <div style="display: flex; justify-content: space-between; margin: 10px 0;">
                    <div>
                        <p style="margin: 5px 0;"><strong>Was:</strong> ${deal.original_price:.2f}</p>
                        <p style="margin: 5px 0;"><strong>Sale:</strong> ${deal.sale_price:.2f}</p>
                        <p style="margin: 5px 0;"><strong>After Coupon:</strong> ${deal.final_price:.2f}</p>
                    </div>
                    <div style="text-align: right;">
                        <p style="margin: 5px 0; font-size: 18px; color: #28a745;">
                            <strong>💰 Save ${deal.savings:.2f}</strong>
                        </p>
                        <p style="margin: 5px 0; color: #28a745;">
                            ({deal.savings_percent:.0f}% off!)
                        </p>
                    </div>
                </div>
                <p style="margin: 5px 0; font-size: 12px; color: #666;">
                    🎫 Coupon: {deal.coupon_description}<br>
                    🏷️ Sale: {deal.sale_description}
                </p>
            </div>
            """
        
        html += """
            <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #28a745; margin: 0 0 10px 0;">📝 Shopping Tips:</h3>
                <ul style="margin: 0; padding-left: 20px;">
                    <li>Open your Giant Food app and "clip" the digital coupons</li>
                    <li>Use your loyalty card when checking out</li>
                    <li>Check expiration dates on both sales and coupons</li>
                    <li>Shop early in the week for best selection</li>
                </ul>
            </div>
            
            <p style="text-align: center; color: #666; font-size: 12px; margin-top: 30px;">
                Generated by Giant Food Deal Tracker<br>
                {datetime.now().strftime('%Y-%m-%d %H:%M')}
            </p>
        </body>
        </html>
        """
        
        return html
    
    def create_email_text(self, deals: List[Deal]) -> str:
        """Create plain text email content"""
        total_savings = sum(deal.savings for deal in deals)
        
        text = f"""🛍️ Giant Food Double-Savings Alert!

Found {len(deals)} deals with both sales AND digital coupons!
💰 Total potential savings: ${total_savings:.2f}

✅ These items are on sale AND have digital coupons
📱 Make sure to clip the coupons in your Giant Food app
⏰ Check expiration dates before shopping

DEALS FOUND:
============
"""
        
        for i, deal in enumerate(deals, 1):
            text += f"""
{i}. {deal.product_name}
   Was: ${deal.original_price:.2f} → Sale: ${deal.sale_price:.2f} → Final: ${deal.final_price:.2f}
   💰 YOU SAVE: ${deal.savings:.2f} ({deal.savings_percent:.0f}% off!)
   🎫 Coupon: {deal.coupon_description}
   🏷️ Sale: {deal.sale_description}
   {'-' * 50}"""
        
        text += f"""

📝 Shopping Tips:
• Open your Giant Food app and "clip" the digital coupons
• Use your loyalty card when checking out
• Check expiration dates on both sales and coupons
• Shop early in the week for best selection

Generated by Giant Food Deal Tracker - {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        
        return text
    
    def run_automated_check(self):
        """Run a complete automated check for deals"""
        start_time = datetime.now()
        logger.info("🤖 Starting automated Giant Food deal check...")
        
        try:
            # Step 1: Scrape digital coupons
            coupons = self.scrape_digital_coupons()
            time.sleep(self.config['scraping']['delay_between_requests'])
            
            # Step 2: Scrape weekly sales
            sales = self.scrape_weekly_sales()
            time.sleep(self.config['scraping']['delay_between_requests'])
            
            # Step 3: Find double deals
            deals = self.find_double_deals(coupons, sales)
            
            # Step 4: Filter new deals (avoid duplicates)
            new_deals = self.filter_new_deals(deals)
            
            # Step 5: Save deals
            if deals:
                self.save_deals(deals)
            
            # Step 6: Send notifications
            if new_deals:
                self.send_email_notification(new_deals)
                self.print_deals_summary(new_deals)
            else:
                logger.info("No new deals found")
            
            # Update previous deals
            self.previous_deals.extend([self.deal_to_dict(deal) for deal in new_deals])
            
            duration = datetime.now() - start_time
            logger.info(f"✅ Automated check completed in {duration.total_seconds():.1f} seconds")
            logger.info(f"Found {len(deals)} total deals, {len(new_deals)} new deals")
            
        except Exception as e:
            logger.error(f"❌ Automated check failed: {e}")
    
    def filter_new_deals(self, deals: List[Deal]) -> List[Deal]:
        """Filter out deals we've already seen recently"""
        new_deals = []
        
        # Create set of previous deal signatures
        previous_signatures = set()
        cutoff_date = datetime.now() - timedelta(days=3)  # Only check last 3 days
        
        for prev_deal in self.previous_deals:
            try:
                deal_date = datetime.fromisoformat(prev_deal.get('found_date', ''))
                if deal_date > cutoff_date:
                    signature = f"{prev_deal['product_name']}_{prev_deal['final_price']}"
                    previous_signatures.add(signature)
            except:
                continue
        
        # Filter new deals
        for deal in deals:
            signature = f"{deal.product_name}_{deal.final_price}"
            if signature not in previous_signatures:
                new_deals.append(deal)
        
        return new_deals
    
    def deal_to_dict(self, deal: Deal) -> Dict:
        """Convert Deal object to dictionary"""
        return {
            'product_name': deal.product_name,
            'original_price': deal.original_price,
            'sale_price': deal.sale_price,
            'coupon_discount': deal.coupon_discount,
            'final_price': deal.
