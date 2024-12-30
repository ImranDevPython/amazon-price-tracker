import sys
import time
import os
import json
from .tracker import AmazonPriceTracker
from .utils.console import print_colored, Fore, Style
import datetime

def load_default_config():
    """Load default sender credentials"""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'default_config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print_colored(f"Error loading default config: {e}", Fore.RED)
        return None

def get_valid_price(prompt, current_price=None):
    """Get valid price input from user"""
    while True:
        try:
            if current_price:
                price_input = input(f"{prompt} (current: ${current_price}): $").strip()
            else:
                price_input = input(f"{prompt}: $").strip()
            
            if not price_input and current_price:
                return current_price
            
            price = float(price_input)
            if price <= 0:
                print_colored("Price must be greater than 0!", Fore.RED)
                continue
            return price
        except ValueError:
            print_colored("Please enter a valid number!", Fore.RED)

def format_product_display(product, index=None, show_url=True):
    """Format product information for display"""
    lines = []
    
    # Product header with number if provided
    if index is not None:
        lines.append(print_colored(f"\n{index}. {product.title[:100]}...", Fore.CYAN, return_str=True))
    else:
        lines.append(print_colored(f"\n{product.title[:100]}...", Fore.CYAN, return_str=True))
    
    # Price information
    lines.append(print_colored(f"   💰 Current Price: ${product.current_price}", Fore.YELLOW, return_str=True))
    lines.append(print_colored(f"   🎯 Target Price:  ${product.target_price}", Fore.YELLOW, return_str=True))
    
    # Savings calculation
    savings = product.current_price - product.target_price
    if savings > 0:
        lines.append(print_colored(f"   💫 Potential Savings: ${savings:.2f}", Fore.GREEN, return_str=True))
    
    # URL (optional)
    if show_url:
        # Truncate URL for cleaner display
        url = product.url.split('?')[0][:100] + "..."
        lines.append(print_colored(f"   🔗 URL: {url}", Fore.WHITE, return_str=True))
    
    # Last checked time
    if product.last_checked:
        last_check = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(product.last_checked))
        lines.append(print_colored(f"   🕒 Last Checked: {last_check}", Fore.WHITE, return_str=True))
    
    return "\n".join(lines)

def format_time(seconds):
    """Format seconds into hours, minutes, seconds"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    if hours > 0:
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    elif minutes > 0:
        return f"{int(minutes)}m {int(seconds)}s"
    else:
        return f"{int(seconds)}s"

def display_countdown(seconds):
    """Display a countdown timer"""
    try:
        while seconds > 0:
            sys.stdout.write('\r')
            time_left = format_time(seconds)
            sys.stdout.write(f"⏳ Next check in: {time_left}   ")
            sys.stdout.flush()
            time.sleep(1)
            seconds -= 1
        sys.stdout.write('\r' + ' ' * 50 + '\r')  # Clear the line
        sys.stdout.flush()
    except KeyboardInterrupt:
        raise

def main():
    """Main function to run the price tracker"""
    print_colored("\n=== Amazon Price Tracker ===", Fore.CYAN, Style.BRIGHT)
    
    # Load default sender credentials
    default_config = load_default_config()
    if not default_config:
        print_colored("\nError: Default credentials not found!", Fore.RED)
        sys.exit(1)
    
    email_sender = default_config['sender_email']
    email_password = default_config['app_password']
    
    # Create tracker instance without receiver email
    tracker = AmazonPriceTracker(email_sender, email_password)
    
    while True:
        try:
            print_colored("\nMenu:", Fore.CYAN)
            print_colored("1. Add new product to track", Fore.WHITE)
            print_colored("2. Remove product from tracking", Fore.WHITE)
            print_colored("3. View tracked products", Fore.WHITE)
            print_colored("4. Start monitoring", Fore.WHITE)
            print_colored("5. Exit", Fore.WHITE)
            
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == "1":
                url = input("\nEnter Amazon product URL: ").strip()
                
                # First fetch product details
                print_colored("\n🔍 Fetching product details...", Fore.CYAN, Style.BRIGHT)
                price, title = tracker.get_product_price(url)
                if price and title:
                    print_colored("\n✨ Product Details:", Fore.CYAN)
                    print_colored(f"📦 Title: {title[:100]}...", Fore.WHITE)
                    print_colored(f"💰 Current Price: ${price}", Fore.YELLOW)
                    
                    # Now ask for target price
                    target_price = get_valid_price("\nEnter target price", price)
                    
                    # Show a summary before confirming
                    print_colored("\n📋 Summary:", Fore.CYAN)
                    print_colored(f"📦 Product: {title[:100]}...", Fore.WHITE)
                    print_colored(f"💰 Current Price: ${price}", Fore.YELLOW)
                    print_colored(f"🎯 Target Price: ${target_price}", Fore.YELLOW)
                    
                    if target_price >= price:
                        print_colored("\n⚠️ Warning: Target price is higher than current price!", Fore.YELLOW)
                        confirm = input("Do you still want to add this product? (y/n): ").strip().lower()
                        if confirm != 'y':
                            print_colored("Product not added.", Fore.YELLOW)
                            continue
                    
                    # Create product with already fetched data
                    if tracker.add_product_with_data(url, target_price, title, price):
                        print_colored("\n✅ Product added successfully!", Fore.GREEN)
                        
                        # Show savings potential
                        savings = price - target_price
                        if savings > 0:
                            print_colored(f"💫 Potential savings: ${savings:.2f} (${price} → ${target_price})", Fore.GREEN)
                    else:
                        print_colored("\n❌ Failed to add product. Please try again.", Fore.RED)
                else:
                    print_colored("\n❌ Failed to fetch product details. Please check the URL and try again.", Fore.RED)
            
            elif choice == "2":
                products = tracker.get_product_list()
                if products:
                    print_colored("\n📋 Tracked Products:", Fore.CYAN)
                    for i, product in enumerate(products, 1):
                        print(format_product_display(product, i, show_url=False))
                    
                    while True:
                        try:
                            index = int(input("\nEnter product number to remove: ").strip()) - 1
                            if 0 <= index < len(products):
                                break
                            print_colored("Invalid product number!", Fore.RED)
                        except ValueError:
                            print_colored("Please enter a valid number!", Fore.RED)
                    
                    # Show product details before removing
                    product = products[index]
                    print_colored(f"\n⚠️ Removing:", Fore.YELLOW)
                    print(format_product_display(product))
                    confirm = input("\nAre you sure? (y/n): ").strip().lower()
                    if confirm == 'y':
                        if tracker.remove_product(index):
                            print_colored("\n✅ Product removed successfully!", Fore.GREEN)
                    else:
                        print_colored("\nProduct not removed.", Fore.YELLOW)
                else:
                    print_colored("\nNo products being tracked.", Fore.YELLOW)
            
            elif choice == "3":
                products = tracker.get_product_list()
                if products:
                    print_colored("\n📋 Tracked Products:", Fore.CYAN)
                    
                    # Show cached data first
                    for i, product in enumerate(products, 1):
                        print(format_product_display(product, i))
                    
                    # Ask if user wants to update prices
                    update = input("\nUpdate prices now? (y/n): ").strip().lower() == 'y'
                    if update:
                        print_colored("\n🔄 Updating prices...", Fore.CYAN)
                        updated = tracker.update_prices(force=True)
                        if updated:
                            print_colored(f"\n✅ Updated prices for {len(updated)} products:", Fore.GREEN)
                            for product in updated:
                                print(format_product_display(product))
                        else:
                            print_colored("No prices needed updating.", Fore.YELLOW)
                else:
                    print_colored("\nNo products being tracked.", Fore.YELLOW)
            
            elif choice == "4":
                products = tracker.get_product_list()
                if not products:
                    print_colored("\nNo products to monitor. Please add products first.", Fore.YELLOW)
                    continue

                # Get receiver's email only when starting monitoring
                email_receiver = input("\nEnter receiver's email address: ").strip()
                tracker.set_receiver_email(email_receiver)
                
                # Show monitoring summary
                print_colored(f"\n📊 Monitoring Summary:", Fore.CYAN)
                print_colored(f"📦 Products being tracked: {len(products)}", Fore.WHITE)
                total_potential_savings = sum(p.current_price - p.target_price for p in products if p.current_price > p.target_price)
                if total_potential_savings > 0:
                    print_colored(f"💫 Total potential savings: ${total_potential_savings:.2f}", Fore.GREEN)
                
                # Get check interval
                while True:
                    try:
                        interval = input("\nCheck interval in hours (default: 1): ").strip()
                        interval = float(interval) if interval else 1
                        if interval <= 0:
                            print_colored("Interval must be greater than 0!", Fore.RED)
                            continue
                        interval = int(interval * 3600)  # Convert hours to seconds
                        break
                    except ValueError:
                        print_colored("Please enter a valid number!", Fore.RED)
                
                print_colored("\n🚀 Monitoring started! Press Ctrl+C to stop.", Fore.GREEN)
                print_colored("📧 You will receive an email when prices drop below target.", Fore.WHITE)
                try:
                    while True:
                        # Force update on first check
                        print_colored("\n🔄 Checking prices...", Fore.CYAN)
                        tracker.check_prices(force_update=True)
                        
                        # Display countdown until next check
                        print_colored(f"\n⏰ Next check in {interval // 3600} hour(s)...", Fore.CYAN)
                        display_countdown(interval)
                except KeyboardInterrupt:
                    print_colored("\n\n🛑 Stopping price monitoring...", Fore.YELLOW)
            
            elif choice == "5":
                if tracker.get_product_list():
                    print_colored("\nWarning: You have tracked products that will stop being monitored.", Fore.YELLOW)
                    confirm = input("Are you sure you want to exit? (y/n): ").strip().lower()
                    if confirm != 'y':
                        continue
                print_colored("\nGoodbye! 👋", Fore.GREEN)
                break
            
            else:
                print_colored("\nInvalid choice. Please try again.", Fore.RED)
                
        except KeyboardInterrupt:
            print_colored("\n\nExiting...", Fore.YELLOW)
            break
        except Exception as e:
            print_colored(f"\nAn error occurred: {e}", Fore.RED)
            print_colored("Please try again.", Fore.YELLOW)

if __name__ == "__main__":
    main()
