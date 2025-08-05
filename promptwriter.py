import os
import google.generativeai as genai
from dotenv import load_dotenv
import shutil

load_dotenv()



genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')



def generate_robot_prompt_from_content(email_file_path: str):

    try:
        with open(email_file_path, 'r', encoding='utf-8') as f:
            email_content = f.read()

        SAVED_MAILS_DIR = os.getenv('SAVED_MAILS_DIR', 'savedmails')
        SAVED_PROMPTS_DIR = os.getenv('SAVED_PROMPTS_DIR', 'savedprompts')
        CONSTANT_APPEND_LINE = os.getenv('CONSTANT_APPEND_LINE')

        print(f"Generating prompt from email content...")
        
        gemini_prompt = f"""
        Extract the following information from the customer booking confirmation email content provided below:
        - Bullet List of Information

        Format this information into this text below, keeping the exact text: 
        
       (This here will be the prompt for the browser AI tool that mostly looks like: go to the given date, click on the given product etc.)
        

        That's it. Also please remeber some important formatting rules:
        - Do not add any introductory or concluding remarks, explanations, or extra text. Provide ONLY the text I asked for.

        Email Content:
        ---
        {email_content}
        ---
        """
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(gemini_prompt)
        robot_command = response.text.strip()

        if robot_command:
            """ This was a trick I used because I realised most of the prompt was constant and only a bit at the
                beginning was going to change, so why send the whole thing to the API and increase my input tokens unnecessarily"""
            final_output_content = robot_command + "\n" + CONSTANT_APPEND_LINE

            original_basename = os.path.basename(email_file_path)
            name, ext = os.path.splitext(original_basename)
            
            new_email_filename = f"processed_{name}{ext}"

            new_email_file_path = os.path.join(SAVED_MAILS_DIR, new_email_filename)
            shutil.move(email_file_path, new_email_file_path)
            print(f"  Archived original email: {original_basename} -> {os.path.basename(new_email_file_path)}")
            return final_output_content
            
        else:
            print("Gemini generated an empty or no response.")
            return False # Indicate failure

    except Exception as e:
        print(f"Error generating prompt: {e}")
        return False # Indicate failure

def process_all_emails_for_prompts():

    processed_count = 0
    failed_count = 0
    
    SAVED_MAILS_DIR = os.getenv('SAVED_MAILS_DIR', 'savedmails')

    SAVED_PROMPTS_DIR = os.getenv('SAVED_PROMPTS_DIR', 'savedprompts') 

    if not os.path.exists(SAVED_MAILS_DIR):
        print(f"Saved mails directory '{SAVED_MAILS_DIR}' does not exist.")
        return 0, 0
    
    os.makedirs(SAVED_PROMPTS_DIR, exist_ok=True)

    email_files_to_process = [f for f in os.listdir(SAVED_MAILS_DIR) if (f.startswith('agency 1') or f.startswith('agency 2')) and f.endswith('.txt')]

    if not email_files_to_process:
        print(f"No new email files found in '{SAVED_MAILS_DIR}' to process for prompts.")
        return 0, 0

    print(f"Found {len(email_files_to_process)} email files in '{SAVED_MAILS_DIR}'.")

    for filename in email_files_to_process:
        email_file_path = os.path.join(SAVED_MAILS_DIR, filename)
        
        generated_prompt_content = generate_robot_prompt_from_content(email_file_path)

        if generated_prompt_content:
            try:
                original_basename_no_ext = os.path.splitext(os.path.basename(email_file_path))[0]
                prompt_filename = f"processed_{original_basename_no_ext}_robot_command.txt"
                prompt_file_path = os.path.join(SAVED_PROMPTS_DIR, prompt_filename)

                with open(prompt_file_path, 'w', encoding='utf-8') as f:
                    f.write(generated_prompt_content)
                
                print(f"  Successfully generated and saved prompt for '{filename}' to '{prompt_filename}'")
                processed_count += 1
            except Exception as e:
                failed_count += 1
                print(f"  Error saving generated prompt for email '{filename}': {e}. The email might still be archived, but no prompt file was created.")
        else:
            failed_count += 1
            print(f"  Failed to generate prompt for email: '{filename}'. It might have been archived by the generator if Gemini returned an empty response.")
    
    print(f"Prompt generation complete. Successfully processed: {processed_count}, Failed: {failed_count}")
    return processed_count, failed_count

if __name__ == "__main__":
    # For testing this script independently
    processed, failed = process_all_emails_for_prompts()
    print(f"Prompt generator run finished. Generated prompts for {processed} emails.")
