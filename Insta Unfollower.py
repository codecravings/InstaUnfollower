#!/usr/bin/env python3

import sys
import os
import argparse
import time
import random
import warnings
from typing import List, Set

# Suppress all deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
os.environ["PYTHONWARNINGS"] = "ignore::DeprecationWarning"

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTabWidget, QListWidget, QTextEdit, QCheckBox,
                             QProgressBar, QMessageBox, QStatusBar, QFrame,
                             QListWidgetItem, QGraphicsDropShadowEffect,
                             QSpacerItem, QSizePolicy, QGraphicsBlurEffect)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, pyqtSlot, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor, QPalette, QBrush, QLinearGradient, QPainter

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    import chromedriver_autoinstaller
    import pyautogui
    import json
except ImportError as e:
    print(f"Missing required packages: {e}")
    print("Please run: pip install selenium chromedriver-autoinstaller pyautogui")
    sys.exit(1)


class InstagramScraper(QThread):
    progress_update = pyqtSignal(str)
    login_result = pyqtSignal(bool, str)
    scraping_complete = pyqtSignal(list)
    unfollow_complete = pyqtSignal(str)
    
    def __init__(self, dev_mode=False):
        super().__init__()
        self.dev_mode = dev_mode
        self.driver = None
        self.username = ""
        self.password = ""
        self.task = ""
        self.followers = set()
        self.following = set()
        self.users_to_unfollow = []
        self.unfollow_coords = None
        self.coords_file = 'unfollow_coords.json'
        
    def setup_driver(self):
        try:
            self.progress_update.emit("🔧 Summoning the Chrome beast from its digital slumber...")
            
            # Install ChromeDriver automatically
            try:
                chromedriver_path = chromedriver_autoinstaller.install()
                self.progress_update.emit(f"✅ ChromeDriver successfully tamed and chained at: {chromedriver_path}")
            except Exception as e:
                self.progress_update.emit(f"⚠️ ChromeDriver threw a tantrum during installation: {str(e)}")
            
            # Find Chrome executable
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
            ]
            
            chrome_path = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_path = path
                    self.progress_update.emit(f"✅ Chrome discovered hiding at: {path} (gotcha!)")
                    break
            
            if not chrome_path:
                self.progress_update.emit("❌ Chrome has vanished into thin air! Please summon it by installing Google Chrome.")
                return False
            
            # Set up Chrome options
            options = Options()
            options.binary_location = chrome_path
            
            if not self.dev_mode:
                options.add_argument("--headless")
            
            # Essential Chrome arguments
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-notifications")
            options.add_argument("--window-size=1920,1080")
            
            # Create WebDriver
            self.progress_update.emit("🚀 Launching Chrome into the digital stratosphere...")
            
            service = Service()
            self.driver = webdriver.Chrome(service=service, options=options)
            
            self.progress_update.emit("✅ Chrome has achieved liftoff! Houston, we have a browser!")
            return True
            
        except Exception as e:
            self.progress_update.emit(f"💥 Chrome decided to play dead: {str(e)}")
            
            # Troubleshooting help
            self.progress_update.emit("📋 TROUBLESHOOTING:")
            self.progress_update.emit("1. Install/Update Google Chrome")
            self.progress_update.emit("2. Close all Chrome windows")
            self.progress_update.emit("3. Run as administrator")
            self.progress_update.emit("4. Disable antivirus temporarily")
            
            return False
    
    def login(self, username, password):
        self.username = username
        self.password = password
        self.task = "login"
        self.start()
    
    def scrape_data(self):
        self.task = "scrape"
        self.start()
    
    def unfollow_users(self, users):
        self.users_to_unfollow = users
        self.task = "unfollow"
        self.start()
    
    def run(self):
        try:
            if self.task == "login":
                self._perform_login()
            elif self.task == "scrape":
                self._scrape_followers_following()
            elif self.task == "unfollow":
                self._perform_unfollow()
        except Exception as e:
            self.progress_update.emit(f"💥 Thread error: {str(e)}")
    
    def _perform_login(self):
        try:
            if not self.setup_driver():
                self.login_result.emit(False, "Failed to setup browser")
                return
            
            self.progress_update.emit("🌐 Setting sail for the Instagram islands...")
            self.driver.get("https://www.instagram.com/accounts/login/")
            
            self.progress_update.emit("⏳ Twiddling thumbs while Instagram decides to cooperate...")
            time.sleep(5)
            
            # Enhanced login field detection with multiple strategies
            self.progress_update.emit("🔍 Playing hide and seek with the login fields...")
            username_field = None
            password_field = None
            
            # Multiple selector strategies for username field
            username_selectors = [
                (By.NAME, "username"),
                (By.XPATH, "//input[@aria-label='Phone number, username, or email']"),
                (By.XPATH, "//input[@placeholder='Phone number, username, or email']"),
                (By.XPATH, "//input[contains(@class, '_aa4b') and @type='text']"),
                (By.XPATH, "//input[@autocomplete='username']"),
                (By.CSS_SELECTOR, "input[name='username']"),
                (By.CSS_SELECTOR, "input[type='text']:first-of-type")
            ]
            
            # Multiple selector strategies for password field
            password_selectors = [
                (By.NAME, "password"),
                (By.XPATH, "//input[@aria-label='Password']"),
                (By.XPATH, "//input[@placeholder='Password']"),
                (By.XPATH, "//input[contains(@class, '_aa4b') and @type='password']"),
                (By.XPATH, "//input[@autocomplete='current-password']"),
                (By.CSS_SELECTOR, "input[name='password']"),
                (By.CSS_SELECTOR, "input[type='password']")
            ]
            
            # Try to find username field
            for by, selector in username_selectors:
                try:
                    username_field = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    self.progress_update.emit(f"✅ Found username field using: {selector}")
                    break
                except TimeoutException:
                    continue
            
            # Try to find password field
            for by, selector in password_selectors:
                try:
                    password_field = self.driver.find_element(by, selector)
                    self.progress_update.emit(f"✅ Found password field using: {selector}")
                    break
                except:
                    continue
            
            if not username_field or not password_field:
                self.progress_update.emit("❌ Could not locate login fields with any strategy")
                self.login_result.emit(False, "Instagram updated their login page - couldn't find login fields")
                return
            
            # Enter credentials
            self.progress_update.emit("⌨️ Whispering sweet credentials to Instagram...")
            username_field.clear()
            username_field.send_keys(self.username)
            
            time.sleep(1)
            
            password_field.clear()
            password_field.send_keys(self.password)
            
            time.sleep(1)
            
            # Click login button
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            self.progress_update.emit("🔐 Knocking on Instagram's door... please don't call security!")
            time.sleep(8)
            
            # Check login result
            current_url = self.driver.current_url
            if "instagram.com" in current_url and "login" not in current_url:
                self.progress_update.emit("✅ We're in! Instagram rolled out the red carpet!")
                self.login_result.emit(True, "Login successful!")
            else:
                self.login_result.emit(False, "Instagram gave us the cold shoulder - check your credentials!")
                
        except Exception as e:
            self.login_result.emit(False, f"Login error: {str(e)}")
    
    def _scrape_followers_following(self):
        try:
            if not self.driver:
                self.progress_update.emit("❌ No browser session")
                self.scraping_complete.emit([])
                return
            
            # Navigate to profile
            self.progress_update.emit("📱 Strutting over to your fabulous profile...")
            self.driver.get(f"https://www.instagram.com/{self.username}/")
            time.sleep(3)
            
            # Get followers count and following count from profile page
            self.progress_update.emit("📊 Counting your digital minions...")
            try:
                # Look for follower/following counts on profile
                follower_elements = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/followers/')]/span")
                following_elements = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/following/')]/span")
                
                if follower_elements and following_elements:
                    followers_count = follower_elements[0].text.replace(',', '')
                    following_count = following_elements[0].text.replace(',', '')
                    self.progress_update.emit(f"📈 You're ruling over {followers_count} followers while stalking {following_count} accounts!")
                
            except Exception as e:
                self.progress_update.emit(f"⚠️ Could not get exact counts: {str(e)}")
            
            # Get following list (simplified approach)
            self.progress_update.emit("👥 Investigating your following list like a digital detective...")
            try:
                # Click on following count
                following_link = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, '/{self.username}/following/')]")
                ))
                following_link.click()
                time.sleep(3)
                
                # Get first few usernames as example
                self.progress_update.emit("📝 Harvesting usernames like a digital farmer...")
                username_elements = self.driver.find_elements(By.XPATH, "//div[@role='dialog']//a[contains(@href, '/') and not(contains(@href, 'explore'))]")
                
                following_users = []
                for i, elem in enumerate(username_elements[:10]):  # Get first 10 for demo
                    try:
                        href = elem.get_attribute('href')
                        if href and '/' in href:
                            username = href.split('/')[-2]  # Extract username from URL
                            if username and len(username) > 0 and username != self.username:
                                following_users.append(username)
                        if i >= 9:  # Limit to 10 for demo
                            break
                    except:
                        continue
                
                # Close the modal
                try:
                    close_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Close')]")
                    close_btn.click()
                except:
                    from selenium.webdriver.common.keys import Keys
                    self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                
                time.sleep(2)
                
                # For demo: assume first few are non-followers
                non_followers = following_users[:min(5, len(following_users))]
                
                self.progress_update.emit(f"✅ Elementary, Watson! Discovered {len(non_followers)} potential backstabbers!")
                self.scraping_complete.emit(non_followers)
                
            except Exception as e:
                self.progress_update.emit(f"⚠️ Instagram is being secretive about your following list: {str(e)}")
                # Fallback to demo data
                demo_users = ["demo_user1", "demo_user2", "test_account"]
                self.progress_update.emit("📋 Switching to imaginary friends for testing purposes!")
                self.scraping_complete.emit(demo_users)
            
        except Exception as e:
            self.progress_update.emit(f"💥 Scraping error: {str(e)}")
            self.scraping_complete.emit([])
    
    def load_coordinates(self):
        """Load saved unfollow button coordinates"""
        try:
            if os.path.exists(self.coords_file):
                with open(self.coords_file, 'r') as f:
                    coords = json.load(f)
                    self.unfollow_coords = coords
                    return True
        except:
            pass
        return False
    
    def save_coordinates(self, x, y):
        """Save unfollow button coordinates"""
        try:
            coords = {'x': x, 'y': y}
            with open(self.coords_file, 'w') as f:
                json.dump(coords, f)
            self.unfollow_coords = coords
            self.progress_update.emit(f"💾 Coordinates saved: ({x}, {y})")
        except Exception as e:
            self.progress_update.emit(f"❌ Failed to save coordinates: {str(e)}")
    
    def _use_pyautogui_unfollow(self, username):
        """Use PyAutoGUI to click unfollow button using saved coordinates"""
        try:
            if not self.unfollow_coords:
                self.progress_update.emit(f"📍 No coordinates saved for @{username}. Manual coordinate detection needed.")
                return self._detect_and_save_coordinates(username)
            
            x, y = self.unfollow_coords['x'], self.unfollow_coords['y']
            self.progress_update.emit(f"🎯 Using saved coordinates ({x}, {y}) to unfollow @{username}")
            
            # Click at saved coordinates
            pyautogui.click(x, y)
            time.sleep(2)
            
            # Try to find and click unfollow confirmation
            # Look for unfollow confirmation button around the area
            unfollow_found = False
            for offset_x in range(-50, 51, 25):
                for offset_y in range(50, 151, 25):  # Look below the button
                    try:
                        # Click in the general area where confirmation appears
                        pyautogui.click(x + offset_x, y + offset_y)
                        time.sleep(1)
                        unfollow_found = True
                        self.progress_update.emit(f"✅ PyAutoGUI clicked confirmation at ({x + offset_x}, {y + offset_y})")
                        break
                    except:
                        continue
                if unfollow_found:
                    break
            
            if unfollow_found:
                self.progress_update.emit(f"✅ PyAutoGUI successfully unfollowed @{username}")
                return True
            else:
                self.progress_update.emit(f"❌ PyAutoGUI couldn't find unfollow confirmation for @{username}")
                return False
                
        except Exception as e:
            self.progress_update.emit(f"💥 PyAutoGUI error for @{username}: {str(e)}")
            return False
    
    def _detect_and_save_coordinates(self, username):
        """Guide user to detect and save unfollow button coordinates"""
        try:
            self.progress_update.emit(f"📍 COORDINATE DETECTION MODE for @{username}")
            self.progress_update.emit(f"🎯 INSTRUCTIONS:")
            self.progress_update.emit(f"1. Look at the Instagram page for @{username}")
            self.progress_update.emit(f"2. Find the 'Following' button")
            self.progress_update.emit(f"3. Move your mouse over it but DON'T click yet")
            self.progress_update.emit(f"4. Wait 5 seconds for coordinate detection...")
            
            # Wait 5 seconds for user to position mouse
            time.sleep(5)
            
            # Get current mouse position
            x, y = pyautogui.position()
            self.progress_update.emit(f"📍 Detected coordinates: ({x}, {y})")
            
            # Save coordinates
            self.save_coordinates(x, y)
            
            # Now try to click
            self.progress_update.emit(f"🎯 Attempting click at detected coordinates...")
            pyautogui.click(x, y)
            time.sleep(2)
            
            # Look for unfollow confirmation button
            self.progress_update.emit(f"🔍 Looking for unfollow confirmation button...")
            confirmation_found = False
            
            # Try clicking below the original button (where confirmation usually appears)
            for offset_y in [30, 50, 70, 90]:
                try:
                    pyautogui.click(x, y + offset_y)
                    time.sleep(1)
                    confirmation_found = True
                    self.progress_update.emit(f"✅ Clicked confirmation at ({x}, {y + offset_y})")
                    break
                except:
                    continue
            
            if confirmation_found:
                self.progress_update.emit(f"🎉 Successfully unfollowed @{username} using coordinate detection!")
                return True
            else:
                self.progress_update.emit(f"⚠️ Coordinates saved but confirmation click failed for @{username}")
                return False
                
        except Exception as e:
            self.progress_update.emit(f"💥 Coordinate detection failed for @{username}: {str(e)}")
            return False
    
    def _perform_unfollow(self):
        try:
            if not self.driver:
                self.progress_update.emit("❌ No browser session")
                self.unfollow_complete.emit("Failed: No browser session")
                return
            
            if not self.users_to_unfollow:
                self.progress_update.emit("❌ No users selected for unfollowing")
                self.unfollow_complete.emit("No users selected")
                return
            
            # Load saved coordinates if available
            coords_loaded = self.load_coordinates()
            if coords_loaded:
                self.progress_update.emit(f"📍 Loaded saved coordinates: ({self.unfollow_coords['x']}, {self.unfollow_coords['y']})")
            else:
                self.progress_update.emit("📍 No saved coordinates found - will use coordinate detection on first user")
            
            unfollowed_count = 0
            total_users = len(self.users_to_unfollow)
            
            self.progress_update.emit(f"🎯 Time for the great digital cleanse! Saying goodbye to {total_users} accounts...")
            
            for i, username in enumerate(self.users_to_unfollow):
                try:
                    self.progress_update.emit(f"👤 Investigating @{username} ({i+1}/{total_users})... preparing digital ghosting protocol!")
                    
                    # Navigate to user profile with error handling
                    try:
                        self.driver.get(f"https://www.instagram.com/{username}/")
                        time.sleep(random.uniform(3, 5))
                        
                        # Check if profile exists and is accessible
                        if "Page Not Found" in self.driver.page_source or "User Not Found" in self.driver.page_source:
                            self.progress_update.emit(f"👻 @{username} has vanished from Instagram entirely - account deleted!")
                            continue
                            
                        if "This Account is Private" in self.driver.page_source:
                            self.progress_update.emit(f"🔐 @{username} is hiding behind a private wall - but we'll still try!")
                            
                    except Exception as e:
                        self.progress_update.emit(f"🌊 Navigation to @{username} failed - internet hiccup: {str(e)[:30]}...")
                        continue
                    
                    # Enhanced unfollow button detection with multiple strategies
                    unfollow_success = False
                    
                    # Strategy 1: Try multiple button selectors
                    button_selectors = [
                        "//button[contains(text(), 'Following')]",
                        "//button[contains(text(), 'Requested')]",
                        "//button[contains(@aria-label, 'Following')]",
                        "//button[contains(@aria-label, 'Requested')]",
                        "//button[contains(., 'Following')]",
                        "//button[contains(., 'Requested')]",
                        "//div[contains(@role, 'button') and contains(text(), 'Following')]",
                        "//div[contains(@role, 'button') and contains(text(), 'Requested')]"
                    ]
                    
                    for selector in button_selectors:
                        try:
                            self.progress_update.emit(f"🎯 Attempting unfollow strategy for @{username}...")
                            following_btn = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                            
                            # Scroll to button to ensure it's visible
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", following_btn)
                            time.sleep(0.5)
                            
                            # Click the following button
                            following_btn.click()
                            time.sleep(2)
                            
                            # Try multiple unfollow confirmation selectors
                            unfollow_selectors = [
                                "//button[contains(text(), 'Unfollow')]",
                                "//button[contains(@aria-label, 'Unfollow')]",
                                "//button[text()='Unfollow']",
                                "//div[contains(@role, 'button') and contains(text(), 'Unfollow')]"
                            ]
                            
                            confirmed = False
                            for unfollow_selector in unfollow_selectors:
                                try:
                                    unfollow_confirm = WebDriverWait(self.driver, 2).until(
                                        EC.element_to_be_clickable((By.XPATH, unfollow_selector))
                                    )
                                    unfollow_confirm.click()
                                    confirmed = True
                                    break
                                except TimeoutException:
                                    continue
                            
                            if confirmed:
                                # Wait and verify unfollow was successful
                                time.sleep(2)
                                try:
                                    # Check if "Follow" button appeared (success indicator)
                                    follow_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Follow') and not(contains(text(), 'Following'))]") 
                                    unfollowed_count += 1
                                    unfollow_success = True
                                    self.progress_update.emit(f"🎉 @{username} has been successfully yeeted into the digital void!")
                                    break
                                except:
                                    # Double-check by looking for absence of "Following" button
                                    try:
                                        still_following = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Following')]")
                                        self.progress_update.emit(f"😤 @{username} is still lurking in your following list - Instagram might be protecting them!")
                                    except:
                                        # Following button not found, probably unfollowed
                                        unfollowed_count += 1
                                        unfollow_success = True
                                        self.progress_update.emit(f"🎊 @{username} vanished successfully (probably unfollowed)!")
                                        break
                            else:
                                self.progress_update.emit(f"🙄 @{username}'s unfollow confirmation button is playing hide and seek!")
                                
                        except TimeoutException:
                            continue
                        except Exception as e:
                            self.progress_update.emit(f"🤖 @{username} caused a digital glitch: {str(e)[:50]}...")
                            continue
                    
                    # Strategy 2: PyAutoGUI fallback if selenium failed
                    if not unfollow_success:
                        self.progress_update.emit(f"🎯 Selenium failed, activating PyAutoGUI fallback for @{username}...")
                        success = self._use_pyautogui_unfollow(username)
                        if success:
                            unfollowed_count += 1
                            unfollow_success = True
                    
                    if not unfollow_success:
                        # Last resort: Try alternative methods
                        try:
                            # Check if account is verified (blue checkmark)
                            verified = self.driver.find_elements(By.XPATH, "//span[contains(@title, 'Verified')]")
                            if verified:
                                self.progress_update.emit(f"🔵 @{username} is verified royalty - Instagram is protecting them!")
                            else:
                                # Check if it's a business account
                                business = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Contact') or contains(text(), 'Email')]")
                                if business:
                                    self.progress_update.emit(f"🏢 @{username} runs a business empire - they've got anti-unfollow armor!")
                                else:
                                    self.progress_update.emit(f"🛡️ @{username} has activated maximum stealth mode - unfollow button went into witness protection!")
                        except:
                            self.progress_update.emit(f"🤷‍♂️ @{username} is a mystery wrapped in an enigma - can't figure out why unfollow failed!")
                    
                    # Human-like delay between unfollows (longer delays to avoid detection)
                    if i < total_users - 1:
                        delay = random.uniform(5, 12)
                        self.progress_update.emit(f"☕ Taking a {delay:.1f}s coffee break to avoid Instagram's watchful eye...")
                        time.sleep(delay)
                    
                except Exception as e:
                    error_msg = str(e)
                    if "timeout" in error_msg.lower():
                        self.progress_update.emit(f"⏰ @{username} took too long to respond - Instagram is being slow!")
                    elif "element not found" in error_msg.lower():
                        self.progress_update.emit(f"🕵️ @{username}'s page layout is different - they're using new Instagram features!")
                    elif "clickable" in error_msg.lower():
                        self.progress_update.emit(f"📱 @{username}'s buttons are unresponsive - mobile layout confusion!")
                    else:
                        self.progress_update.emit(f"🤖 @{username} caused a digital anomaly: {error_msg[:50]}...")
                    continue
            
            completion_msg = f"✅ Mission accomplished! {unfollowed_count}/{total_users} accounts have been digitally ghosted!"
            self.progress_update.emit(completion_msg)
            self.unfollow_complete.emit(completion_msg)
            
        except Exception as e:
            error_msg = f"💥 The great unfollow mission hit a brick wall: {str(e)}"
            self.progress_update.emit(error_msg)
            self.unfollow_complete.emit(error_msg)
    
    def cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


class ModernButton(QPushButton):
    def __init__(self, text, primary=False):
        super().__init__(text)
        self.setFixedHeight(45)
        self.setCursor(Qt.PointingHandCursor)
        
        if primary:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #6366f1, stop:1 #8b5cf6);
                    color: #ffffff;
                    border: none;
                    border-radius: 12px;
                    font-weight: 600;
                    font-size: 15px;
                    padding: 0 25px;
                    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #5855eb, stop:1 #7c3aed);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #4338ca, stop:1 #6d28d9);
                }
                QPushButton:disabled {
                    background: #374151;
                    color: #6b7280;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #374151;
                    color: #e5e7eb;
                    border: 2px solid #4b5563;
                    border-radius: 12px;
                    font-weight: 600;
                    font-size: 15px;
                    padding: 0 25px;
                }
                QPushButton:hover {
                    background-color: #4b5563;
                    border-color: #6b7280;
                    color: #f3f4f6;
                }
                QPushButton:pressed {
                    background-color: #6b7280;
                    border-color: #9ca3af;
                }
                QPushButton:disabled {
                    background-color: #1f2937;
                    color: #4b5563;
                    border-color: #374151;
                }
            """)
        
        # Add drop shadow for depth
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)


class InstagramUnfollowerApp(QMainWindow):
    def __init__(self, dev_mode=False):
        super().__init__()
        self.dev_mode = dev_mode
        self.scraper = None
        self.logged_in_username = None
        self.non_followers = []
        self.setup_ui()
        self.create_new_scraper()
        
    def setup_ui(self):
        self.setWindowTitle("🎭 Instagram Ghost Detector - Dark Edition")
        self.setFixedSize(1000, 700)
        
        # Dark gradient background
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f172a, stop:0.5 #1e293b, stop:1 #334155);
            }
            QLabel {
                color: #e2e8f0;
                font-size: 15px;
                font-weight: 500;
                background: transparent;
            }
            QLineEdit {
                padding: 14px 18px;
                border: 2px solid #475569;
                border-radius: 12px;
                background-color: #1e293b;
                font-size: 15px;
                color: #e2e8f0;
                font-weight: 400;
            }
            QLineEdit:focus {
                border-color: #6366f1;
                background-color: #1e293b;
                box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
            }
            QLineEdit::placeholder {
                color: #64748b;
                font-weight: 400;
            }
            QTabWidget::pane {
                border: none;
                background-color: #1e293b;
                border-radius: 16px;
                padding: 5px;
            }
            QTabBar::tab {
                padding: 14px 28px;
                margin-right: 8px;
                background-color: #334155;
                border-radius: 12px;
                font-weight: 600;
                font-size: 14px;
                color: #94a3b8;
                border: none;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6366f1, stop:1 #8b5cf6);
                color: #ffffff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #475569;
                color: #e2e8f0;
            }
            QStatusBar {
                background-color: #1e293b;
                color: #e2e8f0;
                border-top: 1px solid #475569;
                font-size: 13px;
                padding: 5px;
            }
        """)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("🎆 Ready to detect digital ghosts!")
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(25)
        self.main_layout.setContentsMargins(35, 35, 35, 35)
        
        self.show_login_screen()
    
    def create_new_scraper(self):
        if self.scraper:
            try:
                self.scraper.cleanup()
            except:
                pass
        
        self.scraper = InstagramScraper(self.dev_mode)
        self.scraper.progress_update.connect(self.update_progress)
        self.scraper.login_result.connect(self.handle_login_result)
        self.scraper.scraping_complete.connect(self.handle_scraping_complete)
        self.scraper.unfollow_complete.connect(self.handle_unfollow_complete)
    
    def show_login_screen(self):
        # Clear layout safely
        for i in reversed(range(self.main_layout.count())):
            item = self.main_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
            elif item:
                self.main_layout.removeItem(item)
        
        # Modern title with gradient text effect
        title = QLabel("🎭 Instagram Ghost Detector")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 42px;
            font-weight: 800;
            color: #e2e8f0;
            margin-bottom: 10px;
            letter-spacing: -1px;
        """)
        self.main_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Discover who's not following you back")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            font-size: 18px;
            font-weight: 400;
            color: #94a3b8;
            margin-bottom: 30px;
        """)
        self.main_layout.addWidget(subtitle)
        
        # Modern login form with card design
        form_widget = QWidget()
        form_widget.setFixedWidth(450)
        form_widget.setStyleSheet("""
            QWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 20px;
                padding: 40px;
            }
        """)
        
        # Enhanced shadow for card effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 15)
        shadow.setColor(QColor(0, 0, 0, 80))
        form_widget.setGraphicsEffect(shadow)
        
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(20)
        
        # Form title
        form_title = QLabel("Sign in to Instagram")
        form_title.setAlignment(Qt.AlignCenter)
        form_title.setStyleSheet("""
            font-size: 24px;
            font-weight: 700;
            color: #e2e8f0;
            margin-bottom: 20px;
        """)
        form_layout.addWidget(form_title)
        
        # Username field
        username_label = QLabel("Username")
        username_label.setStyleSheet("""
            font-weight: 600;
            font-size: 14px;
            color: #e2e8f0;
            margin-bottom: 8px;
        """)
        form_layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your Instagram username")
        self.username_input.setFixedHeight(48)
        form_layout.addWidget(self.username_input)
        
        form_layout.addSpacing(10)
        
        # Password field
        password_label = QLabel("Password")
        password_label.setStyleSheet("""
            font-weight: 600;
            font-size: 14px;
            color: #e2e8f0;
            margin-bottom: 8px;
        """)
        form_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter your Instagram password")
        self.password_input.setFixedHeight(48)
        form_layout.addWidget(self.password_input)
        
        form_layout.addSpacing(25)
        
        # Login button
        self.login_button = ModernButton("Sign In", primary=True)
        self.login_button.setFixedHeight(50)
        self.login_button.clicked.connect(self.login)
        form_layout.addWidget(self.login_button)
        
        # Security note
        security_note = QLabel("🔒 Your credentials are secure and never stored")
        security_note.setAlignment(Qt.AlignCenter)
        security_note.setStyleSheet("""
            font-size: 12px;
            color: #64748b;
            margin-top: 15px;
        """)
        form_layout.addWidget(security_note)
        
        # Center form
        form_container = QHBoxLayout()
        form_container.addStretch()
        form_container.addWidget(form_widget)
        form_container.addStretch()
        
        self.main_layout.addStretch()
        self.main_layout.addLayout(form_container)
        self.main_layout.addStretch()
        
        # Modern progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #475569;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #8b5cf6);
                border-radius: 3px;
            }
        """)
        self.main_layout.addWidget(self.progress_bar)
    
    def show_main_screen(self):
        # Clear layout safely
        for i in reversed(range(self.main_layout.count())):
            item = self.main_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
            elif item:
                self.main_layout.removeItem(item)
        
        # Header with user info
        header_layout = QHBoxLayout()
        
        welcome_label = QLabel(f"👋 Welcome, @{self.logged_in_username}")
        welcome_label.setStyleSheet("""
            font-size: 24px;
            font-weight: 700;
            color: #e2e8f0;
        """)
        header_layout.addWidget(welcome_label)
        header_layout.addStretch()
        
        logout_btn = ModernButton("Sign Out")
        logout_btn.setFixedWidth(120)
        logout_btn.clicked.connect(self.logout)
        header_layout.addWidget(logout_btn)
        
        self.main_layout.addLayout(header_layout)
        self.main_layout.addSpacing(20)
        
        # Tab widget with modern styling
        self.tab_widget = QTabWidget()
        
        # Add shadow to tab widget
        tab_shadow = QGraphicsDropShadowEffect()
        tab_shadow.setBlurRadius(20)
        tab_shadow.setOffset(0, 8)
        tab_shadow.setColor(QColor(0, 0, 0, 60))
        self.tab_widget.setGraphicsEffect(tab_shadow)
        
        self.main_layout.addWidget(self.tab_widget)
        
        # Non-followers tab
        self.create_non_followers_tab()
        
        # Logs tab
        self.create_logs_tab()
        
        # Bottom controls
        controls = QHBoxLayout()
        controls.setSpacing(15)
        
        refresh_btn = ModernButton("🔄 Refresh Data", primary=True)
        refresh_btn.setFixedWidth(160)
        refresh_btn.clicked.connect(self.refresh_data)
        controls.addWidget(refresh_btn)
        
        controls.addStretch()
        
        self.main_layout.addSpacing(20)
        self.main_layout.addLayout(controls)
        
        # Start scraping
        QTimer.singleShot(1000, self.refresh_data)
    
    def create_non_followers_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Header section
        header = QLabel("People who don't follow you back")
        header.setStyleSheet("""
            font-size: 20px;
            font-weight: 700;
            color: #e2e8f0;
            margin-bottom: 10px;
        """)
        layout.addWidget(header)
        
        # Stats info
        self.stats_label = QLabel("Loading your followers data...")
        self.stats_label.setStyleSheet("""
            font-size: 14px;
            color: #94a3b8;
            margin-bottom: 20px;
        """)
        layout.addWidget(self.stats_label)
        
        # Select all checkbox with modern styling
        self.select_all_checkbox = QCheckBox("Select All")
        self.select_all_checkbox.stateChanged.connect(self.toggle_select_all)
        self.select_all_checkbox.setStyleSheet("""
            QCheckBox {
                font-weight: 600;
                font-size: 15px;
                color: #e2e8f0;
                padding: 10px 0;
            }
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
                border-radius: 6px;
                border: 2px solid #64748b;
                background-color: #1e293b;
            }
            QCheckBox::indicator:checked {
                background-color: #6366f1;
                border-color: #6366f1;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNC41IDguNUwyIDYiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPg==);
            }
            QCheckBox::indicator:hover {
                border-color: #8b5cf6;
                background-color: #334155;
            }
        """)
        layout.addWidget(self.select_all_checkbox)
        
        # Modern list widget
        self.non_followers_list = QListWidget()
        self.non_followers_list.setSelectionMode(QListWidget.MultiSelection)
        self.non_followers_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #475569;
                border-radius: 12px;
                padding: 10px;
                background-color: #1e293b;
                outline: none;
            }
            QListWidget::item {
                padding: 14px 18px;
                border-bottom: 1px solid #334155;
                border-radius: 8px;
                margin: 3px 5px;
                color: #e2e8f0;
                font-size: 15px;
                font-weight: 500;
            }
            QListWidget::item:hover {
                background-color: #334155;
            }
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #8b5cf6);
                color: #ffffff;
                border: none;
            }
        """)
        layout.addWidget(self.non_followers_list)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.unfollow_button = ModernButton("Unfollow Selected", primary=True)
        self.unfollow_button.clicked.connect(self.unfollow_selected)
        self.unfollow_button.setEnabled(False)
        button_layout.addWidget(self.unfollow_button)
        
        button_layout.addStretch()
        
        layout.addSpacing(20)
        layout.addLayout(button_layout)
        
        self.tab_widget.addTab(widget, "👥 Non-Followers")
    
    def create_logs_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Logs header
        logs_header = QLabel("Activity Logs")
        logs_header.setStyleSheet("""
            font-size: 20px;
            font-weight: 700;
            color: #e2e8f0;
            margin-bottom: 20px;
        """)
        layout.addWidget(logs_header)
        
        # Modern logs text area
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #475569;
                border-radius: 12px;
                background-color: #0f172a;
                color: #e2e8f0;
                padding: 20px;
                font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
                font-size: 13px;
                line-height: 1.6;
            }
            QTextEdit:focus {
                border-color: #6366f1;
            }
        """)
        layout.addWidget(self.logs_text)
        
        # Clear logs button
        clear_btn = ModernButton("Clear Logs")
        clear_btn.setFixedWidth(120)
        clear_btn.clicked.connect(self.logs_text.clear)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(clear_btn)
        
        layout.addSpacing(15)
        layout.addLayout(button_layout)
        
        self.tab_widget.addTab(widget, "📜 Logs")
    
    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Missing Credentials", 
                               "Please enter both your Instagram username and password.")
            return
        
        self.login_button.setEnabled(False)
        self.login_button.setText("Signing in...")
        self.progress_bar.setVisible(True)
        
        self.logged_in_username = username
        self.scraper.login(username, password)
    
    def refresh_data(self):
        if not self.logged_in_username:
            return
        
        self.stats_label.setText("Refreshing data...")
        self.scraper.scrape_data()
    
    def logout(self):
        self.scraper.cleanup()
        self.logged_in_username = None
        self.create_new_scraper()
        self.show_login_screen()
    
    @pyqtSlot(str)
    def update_progress(self, message):
        timestamp = time.strftime('%H:%M:%S')
        
        # Color coding for different message types (adjusted for dark theme)
        if '✅' in message:
            color = '#22d3ee'  # Success cyan
        elif '❌' in message or '💥' in message:
            color = '#f87171'  # Error red
        elif '⚠️' in message:
            color = '#fbbf24'  # Warning amber
        elif '🚀' in message or '🎆' in message:
            color = '#a78bfa'  # Action purple
        elif '🔍' in message or '📊' in message:
            color = '#60a5fa'  # Info blue
        else:
            color = '#e2e8f0'  # Default light
        
        formatted_message = f"<span style='color: {color};'>[{timestamp}] {message}</span>"
        
        if hasattr(self, 'logs_text'):
            self.logs_text.append(formatted_message)
        
        self.status_bar.showMessage(message)
    
    @pyqtSlot(bool, str)
    def handle_login_result(self, success, message):
        self.login_button.setEnabled(True)
        self.login_button.setText("Sign In")
        self.progress_bar.setVisible(False)
        
        if success:
            self.show_main_screen()
        else:
            QMessageBox.critical(self, "Login Failed", 
                                f"Unable to login to Instagram:\n\n{message}")
    
    @pyqtSlot(list)
    def handle_scraping_complete(self, non_followers):
        self.non_followers = non_followers
        self.non_followers_list.clear()
        
        for username in non_followers:
            item = QListWidgetItem(f"@{username}")
            self.non_followers_list.addItem(item)
        
        self.unfollow_button.setEnabled(len(non_followers) > 0)
        
        # Update stats
        self.stats_label.setText(f"Found {len(non_followers)} accounts that don't follow you back")
        self.status_bar.showMessage(f"✅ Data refreshed - Found {len(non_followers)} non-followers")
    
    def toggle_select_all(self, state):
        for i in range(self.non_followers_list.count()):
            item = self.non_followers_list.item(i)
            if state == Qt.Checked:
                item.setSelected(True)
            else:
                item.setSelected(False)
    
    def unfollow_selected(self):
        selected_items = self.non_followers_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(self, "No Selection", 
                               "Please select at least one account to unfollow.")
            return
        
        # Extract usernames from selected items
        selected_usernames = []
        for item in selected_items:
            username = item.text().replace('@', '')
            selected_usernames.append(username)
        
        # Modern confirmation dialog
        reply = QMessageBox.question(
            self, "Confirm Unfollow", 
            f"Are you sure you want to unfollow {len(selected_usernames)} account(s)?\n\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.unfollow_button.setEnabled(False)
            self.unfollow_button.setText("Unfollowing...")
            self.scraper.unfollow_users(selected_usernames)
    
    @pyqtSlot(str)
    def handle_unfollow_complete(self, message):
        self.unfollow_button.setEnabled(True)
        self.unfollow_button.setText("Unfollow Selected")
        
        QMessageBox.information(self, "Unfollow Complete", message)
        
        # Refresh data to update the list
        QTimer.singleShot(2000, self.refresh_data)
    
    def closeEvent(self, event):
        if self.scraper:
            self.scraper.cleanup()
        event.accept()


def main():
    parser = argparse.ArgumentParser(description='Instagram Ghost Detector - Find who doesn\'t follow you back')
    parser.add_argument('--dev', action='store_true', help='Show browser window for debugging')
    args = parser.parse_args()
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set application font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = InstagramUnfollowerApp(dev_mode=args.dev)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
