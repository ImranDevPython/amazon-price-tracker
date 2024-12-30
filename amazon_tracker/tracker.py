import requests
from bs4 import BeautifulSoup
import smtplib
import time
import random
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
try:
    from .utils.console import print_colored, Fore, Style
except ImportError:
    from utils.console import print_colored, Fore, Style

class Product:
    def __init__(self, url, target_price, title=None, current_price=None):
        self.url = url
        self.target_price = target_price
        self.title = title
        self.current_price = current_price
        self.last_checked = None
    
    def to_dict(self):
        """Convert product to dictionary for JSON serialization"""
        return {
            'url': self.url,
            'target_price': self.target_price,
            'title': self.title,
            'current_price': self.current_price,
            'last_checked': self.last_checked
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create product from dictionary"""
        product = cls(data['url'], data['target_price'])
        product.title = data['title']
        product.current_price = data['current_price']
        product.last_checked = data['last_checked']
        return product

class AmazonPriceTracker:
    def __init__(self, email_sender, email_password, email_receiver=None):
        self.email_sender = email_sender
        self.email_password = email_password
        self.email_receiver = email_receiver
        self.products = []
        self.products_file = os.path.join(os.path.dirname(__file__), 'data', 'products.json')
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(self.products_file), exist_ok=True)
        
        # Load saved products
        self.load_products()
        
        # List of different User-Agents to rotate
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/120.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        
        self.setup_session()

    def load_products(self):
        """Load products from JSON file"""
        try:
            if os.path.exists(self.products_file):
                with open(self.products_file, 'r') as f:
                    data = json.load(f)
                    self.products = [Product.from_dict(p) for p in data]
        except Exception as e:
            print_colored(f"Error loading products: {e}", Fore.RED)
            self.products = []

    def save_products(self):
        """Save products to JSON file"""
        try:
            with open(self.products_file, 'w') as f:
                json.dump([p.to_dict() for p in self.products], f, indent=2)
        except Exception as e:
            print_colored(f"Error saving products: {e}", Fore.RED)

    def add_product_with_data(self, url, target_price, title, current_price):
        """Add a new product with already fetched data"""
        product = Product(url, target_price)
        product.title = title
        product.current_price = current_price
        product.last_checked = time.time()
        self.products.append(product)
        self.save_products()
        return True

    def add_product(self, url, target_price):
        """Add a new product to track (fetches data first)"""
        price, title = self.get_product_price(url)
        if price and title:
            return self.add_product_with_data(url, target_price, title, price)
        return False

    def remove_product(self, index):
        """Remove a product from tracking"""
        if 0 <= index < len(self.products):
            self.products.pop(index)
            self.save_products()  # Save after removing
            return True
        return False

    def get_product_list(self):
        """Get list of all tracked products"""
        return self.products

    def update_prices(self, force=False):
        """Update prices for all products
        If force is False, only update prices that haven't been checked in the last hour"""
        updated_products = []
        current_time = time.time()
        
        for product in self.products:
            # Skip if checked within last hour and not forced
            if not force and product.last_checked and (current_time - product.last_checked) < 3600:
                continue
                
            price, title = self.get_product_price(product.url)
            if price and title:
                product.current_price = price
                product.title = title
                product.last_checked = current_time
                updated_products.append(product)
        
        if updated_products:
            self.save_products()
        
        return updated_products

    def setup_session(self):
        """Setup a session with retry strategy"""
        self.session = requests.Session()
        
        # Setup retry strategy
        retry_strategy = Retry(
            total=3,  # number of retries
            backoff_factor=1,  # wait 1, 2, 4 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504]  # status codes to retry on
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        # Update headers with a random User-Agent
        self.update_headers()

    def update_headers(self):
        """Update session headers with a random User-Agent"""
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        }
        self.session.headers.update(headers)

    def get_product_price(self, url):
        """Get product price and title from Amazon"""
        try:
            # Add a random delay between 1-3 seconds
            time.sleep(random.uniform(1, 3))
            
            # Update headers with a new random User-Agent
            self.update_headers()
            
            # Make the request
            print_colored("Fetching product details...", Fore.WHITE)
            page = self.session.get(url, timeout=10)
            print_colored(f"Response status code: {page.status_code}", Fore.WHITE)
            
            if page.status_code != 200:
                print_colored(f"Failed to fetch page. Status code: {page.status_code}", Fore.YELLOW)
                if page.status_code == 503:
                    print_colored("Amazon is blocking our request. Waiting longer before retry...", Fore.YELLOW)
                    time.sleep(random.uniform(5, 10))
                return None, None
                
            soup = BeautifulSoup(page.content, 'lxml')
            
            # Get product title
            title = soup.find(id='productTitle')
            if title:
                title = title.get_text().strip()
                print_colored(f"Found title: {title}", Fore.CYAN)
            else:
                print_colored("Title not found", Fore.YELLOW)
            
            # Get product price
            price_element = soup.find('span', class_='a-price-whole')
            if price_element:
                price_text = price_element.get_text().strip()
                try:
                    # Remove commas and dots from the price text
                    price_text = price_text.replace(',', '').replace('.', '')
                    price = float(price_text)
                    print_colored(f"Found price: ${price}", Fore.YELLOW)
                    return price, title
                except ValueError as e:
                    print_colored(f"Error converting price: {price_text}", Fore.YELLOW)
                    return None, None
            else:
                print_colored("Price element not found", Fore.YELLOW)
                print_colored("This might be due to Amazon's anti-bot protection.", Fore.YELLOW)
                return None, None
                
        except requests.exceptions.RequestException as e:
            print_colored(f"Network error: {str(e)}", Fore.RED)
            print_colored("Will retry after delay...", Fore.YELLOW)
            return None, None
        except Exception as e:
            print_colored(f"Error getting product price: {e}", Fore.YELLOW)
            return None, None

    def check_prices(self, force_update=False):
        """Check prices for all tracked products"""
        if not self.email_receiver:
            print_colored("Error: Receiver email not set!", Fore.RED)
            return

        # Only update prices if forced or haven't been checked recently
        updated = self.update_prices(force=force_update)
        if updated:
            print_colored(f"\nUpdated prices for {len(updated)} products", Fore.CYAN)
        
        price_drops = []
        for product in self.products:
            if product.current_price <= product.target_price:
                price_drops.append(product)
                    
            print_colored(f"\nProduct: {product.title}", Fore.CYAN)
            if product.current_price <= product.target_price:
                print_colored(f"Current Price: ${product.current_price} (Below target! 🎯)", Fore.GREEN, Style.BRIGHT)
            else:
                print_colored(f"Current Price: ${product.current_price}", Fore.YELLOW)
                    
        if price_drops:
            self.send_email(price_drops)

    def set_receiver_email(self, email):
        """Set the receiver's email address"""
        self.email_receiver = email

    def send_email(self, products):
        """Send email notification for price drops"""
        if not products:
            return

        try:
            # Create HTML email content
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .header {{
                        background-color: #4CAF50;
                        color: white;
                        padding: 20px;
                        text-align: center;
                        border-radius: 5px 5px 0 0;
                    }}
                    .content {{
                        background-color: #f9f9f9;
                        padding: 20px;
                        border: 1px solid #ddd;
                        border-radius: 0 0 5px 5px;
                    }}
                    .product {{
                        margin-bottom: 20px;
                        padding: 15px;
                        background-color: white;
                        border: 1px solid #eee;
                        border-radius: 5px;
                    }}
                    .price {{
                        color: #4CAF50;
                        font-weight: bold;
                        font-size: 1.2em;
                    }}
                    .savings {{
                        color: #e44d26;
                        font-weight: bold;
                    }}
                    .button {{
                        display: inline-block;
                        padding: 10px 20px;
                        background-color: #4CAF50;
                        color: white;
                        text-decoration: none;
                        border-radius: 5px;
                        margin-top: 10px;
                    }}
                    .button:hover {{
                        background-color: #45a049;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🎉 Price Drop Alert! 🎉</h1>
                </div>
                <div class="content">
                    <p>Good news! The following products have dropped below your target price:</p>
            """

            for product in products:
                savings = product.target_price - product.current_price
                html_content += f"""
                    <div class="product">
                        <h2>📦 {product.title}</h2>
                        <p class="price">Current Price: ${product.current_price:.2f}</p>
                        <p>Target Price: ${product.target_price:.2f}</p>
                        <p class="savings">You Save: ${savings:.2f}! 💰</p>
                        <a href="{product.url}" class="button">View on Amazon</a>
                    </div>
                """

            html_content += """
                    <p style="margin-top: 20px;">Happy shopping! 🛍️</p>
                </div>
            </body>
            </html>
            """

            # Create plain text content as fallback
            text_content = "Price Drop Alert!\n\n"
            for product in products:
                savings = product.target_price - product.current_price
                text_content += f"""
Product: {product.title}
Current Price: ${product.current_price:.2f}
Target Price: ${product.target_price:.2f}
You Save: ${savings:.2f}!
URL: {product.url}

"""

            # Create message container
            msg = MIMEMultipart('alternative')
            msg['Subject'] = '🎉 Amazon Price Drop Alert!'
            msg['From'] = self.email_sender
            msg['To'] = self.email_receiver

            # Add both plain text and HTML parts
            part1 = MIMEText(text_content, 'plain')
            part2 = MIMEText(html_content, 'html')
            msg.attach(part1)
            msg.attach(part2)

            # Send email
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.email_sender, self.email_password)
                server.send_message(msg)

            print_colored("\n✉️ Price drop notification sent!", Fore.GREEN)
        except Exception as e:
            print_colored(f"\n❌ Failed to send email: {e}", Fore.RED)

if __name__ == "__main__":
    print_colored("\n=== Amazon Price Tracker Setup ===", Fore.CYAN, Style.BRIGHT)
    print_colored("\nPlease enter the following information:", Fore.YELLOW)
    
    # Get configuration from user
    try:
        from .utils.config import load_default_config
    except ImportError:
        from utils.config import load_default_config

    default_config = load_default_config()
    if default_config:
        EMAIL_SENDER = default_config.get('sender_email')
        EMAIL_PASSWORD = default_config.get('app_password')
    else:
        print_colored("\nDefault credentials not found. Please enter manually:", Fore.YELLOW)
        EMAIL_SENDER = input("Your Gmail address: ").strip()
        EMAIL_PASSWORD = input("Your Gmail App Password: ").strip()
    
    tracker = AmazonPriceTracker(
        EMAIL_SENDER,
        EMAIL_PASSWORD
    )

    while True:
        print_colored("\n1. Add product to track", Fore.CYAN)
        print_colored("2. Remove product from tracking", Fore.CYAN)
        print_colored("3. Check prices for all products", Fore.CYAN)
        print_colored("4. Set receiver email", Fore.CYAN)
        print_colored("5. Exit", Fore.CYAN)
        
        choice = input("Enter your choice: ").strip()
        
        if choice == "1":
            url = input("Enter Amazon product URL: ").strip()
            while True:
                try:
                    target_price = float(input("Enter target price: ").strip())
                    break
                except ValueError:
                    print_colored("Please enter a valid number!", Fore.RED)
            if tracker.add_product(url, target_price):
                print_colored("Product added successfully!", Fore.GREEN)
            else:
                print_colored("Failed to add product. Please try again.", Fore.RED)
        elif choice == "2":
            products = tracker.get_product_list()
            if products:
                for i, product in enumerate(products):
                    print_colored(f"{i+1}. {product.title} - {product.url}", Fore.CYAN)
                while True:
                    try:
                        index = int(input("Enter the product number to remove: ").strip()) - 1
                        if 0 <= index < len(products):
                            break
                        else:
                            print_colored("Invalid product number. Please try again.", Fore.RED)
                    except ValueError:
                        print_colored("Please enter a valid number!", Fore.RED)
                if tracker.remove_product(index):
                    print_colored("Product removed successfully!", Fore.GREEN)
                else:
                    print_colored("Failed to remove product. Please try again.", Fore.RED)
            else:
                print_colored("No products to remove.", Fore.YELLOW)
        elif choice == "3":
            tracker.check_prices()
        elif choice == "4":
            email = input("Enter receiver email address: ").strip()
            tracker.set_receiver_email(email)
            print_colored("Receiver email set successfully!", Fore.GREEN)
        elif choice == "5":
            print_colored("\nExiting...", Fore.YELLOW)
            break
        else:
            print_colored("Invalid choice. Please try again.", Fore.RED)
