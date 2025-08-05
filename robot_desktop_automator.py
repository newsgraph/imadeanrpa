# robot_desktop_automator.py

import pyautogui
import time
import os
import pyperclip
import shutil 
from dotenv import load_dotenv

load_dotenv()
"""This is my way of interacting with the browser plugin that is the AI agent. This may not work for you
because the tool you use might be designed otherwise. I'm still leaving it here for an insight into how one might give consistent commands to an AI agent
"""
ROBOT_NEW_CHAT_BUTTON_IMAGE = 'filename.png'
ROBOT_ACTUAL_INPUT_AREA_IMAGE = 'filename.png'
ROBOT_SUBMIT_BUTTON_IMAGE = 'filename.png'
BOOKING_CONFIRMATION_IMAGE = 'filename.png'

def click_image_on_screen(image_path: str, confidence=0.9, attempts=3, interval=5) -> tuple:
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at '{image_path}'")
        return None

    print(f"Looking for '{image_path}' on screen...")
    for i in range(attempts):
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence, grayscale=False)
            if location:
                center_x = location.left + location.width // 2
                center_y = location.top + location.height // 2
                pyautogui.click(center_x, center_y)
                print(f"Clicked '{image_path}' at ({center_x}, {center_y}).")
                return (center_x, center_y)
            else:
                print(f"'{image_path}' not found (attempt {i+1}/{attempts}). Retrying...")
                time.sleep(interval)
        except pyautogui.PyAutoGUIException as e:
            print(f"PyAutoGUI error while searching for '{image_path}': {e}")
            time.sleep(interval)
    print(f"Failed to find '{image_path}' after {attempts} attempts.")
    return None

def type_text_into_active_field(text: str):

    pyperclip.copy(text)
    time.sleep(0.5)
    pyautogui.hotkey('ctrl', 'v')
    print(f"Pasted text: '{text[:50]}...'")

def automate_robot_with_command(robot_command: str) -> bool:
    """
    Automates inputting a single natural language command into the extension.
    Returns True on success, False on failure.
    """
    print(f"Attempting to automate robot with command: \n{robot_command[:100]}...")


    # Step 1: Click "New Chat" button
    if 'ROBOT_NEW_CHAT_BUTTON_IMAGE' in globals() and os.path.exists(ROBOT_NEW_CHAT_BUTTON_IMAGE):
        new_chat_clicked = click_image_on_screen(ROBOT_NEW_CHAT_BUTTON_IMAGE, confidence=0.9)
        if not new_chat_clicked:
            print("Could not click 'New Chat' button. Continuing, but input area might not be clear.")
        else:
            time.sleep(1) # Give time for UI to reset

    # Step 2: Click on the actual input text area to activate it
    input_area_clicked = click_image_on_screen(ROBOT_ACTUAL_INPUT_AREA_IMAGE, confidence=0.9)
    if not input_area_clicked:
        print("Failed to activate input area. Automation step aborted.")
        return False
    
    time.sleep(0.5) # Small delay for cursor to appear

    # Step 3: Type (paste) the command into the now-active input field
    type_text_into_active_field(robot_command)

    time.sleep(1) # Small delay before clicking submit button

    # Step 4: Locate and click the submit button
    submit_button_clicked = click_image_on_screen(ROBOT_SUBMIT_BUTTON_IMAGE, confidence=0.9)
    if not submit_button_clicked:
        print("Failed to click submit button. Automation step aborted.")
        return False

    print("Command submitted. Waiting for robot.ai action.")
    time.sleep(7) # Wait to observe the result of the command

    
    return True

def process_all_pending_robot_prompts():

    processed_count = 0
    failed_count = 0
    SAVED_MAILS_DIR = os.getenv('SAVED_MAILS_DIR', 'savedmails')
    SAVED_PROMPTS_DIR = os.getenv('SAVED_PROMPTS_DIR', 'savedprompts')
    COMPLETED_PROMPTS_DIR = os.getenv('COMPLETED_PROMPTS_DIR', 'complete')
    if not os.path.exists(SAVED_PROMPTS_DIR):
        print(f"Saved prompts directory '{SAVED_PROMPTS_DIR}' does not exist.")
        return 0, 0

    pending_prompt_files = [f for f in os.listdir(SAVED_PROMPTS_DIR) if f.startswith('processed_') and f.endswith('.txt')]

    if not pending_prompt_files:
        print(f"No new pending robot.ai prompt files found in '{SAVED_PROMPTS_DIR}' to process.")
        return 0, 0

    print(f"Found {len(pending_prompt_files)} pending robot.ai prompt files in '{SAVED_PROMPTS_DIR}'.")

    for filename in pending_prompt_files:
        prompt_file_path = os.path.join(SAVED_PROMPTS_DIR, filename)
        try:
            with open(prompt_file_path, 'r', encoding='utf-8') as f:
                robot_command_content = f.read().strip() # Corrected: Added () to .strip()

            if not robot_command_content:
                print(f"  Warning: Prompt file {filename} is empty. Skipping and marking as empty_failed.")
                failed_count += 1
                # Rename empty files so they don't block future runs
                # Replace 'processed_' with 'empty_robot_command_' for clarity
                empty_filename = filename.replace('processed_', 'empty_robot_command_', 1)
                shutil.move(prompt_file_path, os.path.join(SAVED_PROMPTS_DIR, empty_filename))
                continue

            # Attempt to automate the command
            if automate_robot_with_command(robot_command_content):
                # On success, rename from 'processed_' to 'completed_robot_command_'
                new_filename = filename.replace('processed_', 'completed_', 1)
                shutil.move(prompt_file_path, os.path.join(COMPLETED_PROMPTS_DIR, new_filename))
                print(f"  Archived processed prompt: {filename} -> {new_filename}")
                processed_count += 1
            else:
                # On failure, rename from 'processed_' to 'failed_robot_command_'
                failed_count += 1
                print(f"  Failed to automate prompt for: {filename}. Renaming to indicate failure.")
                failed_filename = filename.replace('processed_', 'failed_robot_command_', 1)
                shutil.move(prompt_file_path, os.path.join(SAVED_PROMPTS_DIR, failed_filename))

        except Exception as e:
            failed_count += 1
            print(f"Error processing file {filename}: {e}. It remains in its current state ('processed_') for manual review/retry.")

    print(f"\nautomation complete. Successfully processed: {processed_count}, Failed: {failed_count}")
    return processed_count, failed_count

if __name__ == "__main__":
    print(f"Starting robot automation. Reading from: {SAVED_PROMPTS_DIR}")


    try:
        all_windows = pyautogui.getWindowsWithTitle('')
        chrome_windows = [
            win for win in all_windows
            if "Chrome" in win.title and win.is_visible
        ]

        if chrome_windows:
            chrome_windows[0].activate()
            print(f"Activated Chrome window: '{chrome_windows[0].title}'")
            time.sleep(1)
        else:
            print("Chrome window not found. Please ensure Chrome is open and active.")
            sys.exit(1) # Exit the script if Chrome is not found
    except Exception as e:
        print(f"Error activating Chrome window: {e}")
        sys.exit(1)

    processed, failed = process_all_pending_robot_prompts()
    print(f"Rtrvr automation run finished. Automated {processed} prompts.")
