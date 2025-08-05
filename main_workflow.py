# main_workflow.py

import sys
import os
from dotenv import load_dotenv

load_dotenv()

import time
from datetime import datetime
import pyautogui


project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from mailfetcher import fetch_emails
from promptwriter import process_all_emails_for_prompts 
from robot_desktop_automator import process_all_pending_robot_prompts

load_dotenv()

# --- Configuration for the Orchestrator ---
IMAP_HOST = os.getenv('EMAIL_HOST')
IMAP_PORT = int(os.getenv('EMAIL_PORT'))
IMAP_USER = os.getenv('EMAIL_USER')
IMAP_PASS = os.getenv('EMAIL_PASS')
EMAIL_OUTPUT_BASE_DIR = os.getenv('EMAIL_OUTPUT_BASE_DIR')
ROBOT_PROMPTS_DIR = os.getenv('SAVED_PROMPTS_DIR')

def run_full_workflow():
    print(f"\n--- Workflow initiated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")

    # 1. Email Retrieval
    print("\nStarting Email Retrieval...")
    try:

        saved_emails = fetch_emails(
            host=IMAP_HOST,
            port=IMAP_PORT,
            username=IMAP_USER,
            password=IMAP_PASS,
            output_base_dir=EMAIL_OUTPUT_BASE_DIR,
            mark_as_read=True
        )
        print(f"Email retrieval completed. Found and processed {len(saved_emails)} new emails.")
    except Exception as e:
        print(f"Error during Email Retrieval: {e}")
        
        pass 

    # 2. Prompt Generation
    print("\nStarting Prompt Generation...")
    try:

        processed_for_prompts, failed_for_prompts = process_all_emails_for_prompts()
        print(f"Prompt generation completed. Generated {processed_for_prompts} prompts.")
        if failed_for_prompts > 0:
            print(f"  WARNING: {failed_for_prompts} emails failed prompt generation.")
    except Exception as e:
        print(f"Error during Prompt Generation: {e}")
        pass

    # 3. Browser Automation
    print("\nStarting Browser Automation...")

    time.sleep(2) 

    try:

        all_windows = pyautogui.getWindowsWithTitle('')
        
        
        chrome_windows = [
            win for win in all_windows
            if "Chrome" in win.title
        ]

        if chrome_windows:

            chrome_windows[0].activate()
            print(f"Activated Chrome window: '{chrome_windows[0].title}'")
            time.sleep(2)
        else:
            print("Error: Chrome window not found. Please ensure Chrome is open and active before running the workflow.")
            sys.exit(1)
    except Exception as e:
        print(f"An error occurred while trying to activate Chrome: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while trying to activate Chrome: {e}")
        sys.exit(1)

    try:
        processed_robot_prompts, failed_robot_prompts = process_all_pending_robot_prompts()
        print(f"Browser automation completed. Automated {processed_robot_prompts} prompts.")
        if failed_robot_prompts > 0:
            print(f"  WARNING: {failed_robot_prompts} prompts failed automation.")
    except Exception as e:
        print(f"Error during Browser Automation: {e}")
        pass

    print(f"\n--- Workflow finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")

if __name__ == "__main__":

    run_full_workflow()
