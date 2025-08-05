import os
import ssl
import re
from dotenv import load_dotenv
from imapclient import IMAPClient
from email.message import EmailMessage
from email.parser import BytesParser
from datetime import datetime, date

# You don't want any email to run the rest of the script. Also since I'm storing emails that come from two sources this tag is a way to identify them
EMAIL_SUBJECT_PATTERNS = {
    r" ": "tag",
    r"": "tag2"
}

# This approach is good if you are reading template emails which always follow their structures. Helps reduce tokens. Ref line 55
CONTENT_MARKERS = {
    "tag": {
        "start": "",
        "end": ""
    },
    "tag2": {
        "start": "",
        "end": ""
    }
}


def get_next_daily_sequence_from_files(output_dir: str, sender_type: str, email_date: datetime) -> int:

    date_for_filename = email_date.strftime('%Y%m%d')
    max_sequence = 0
    
    filename_prefix = f"{sender_type}_{today_str_for_filename}_"
    
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            expected_min_len = len(filename_prefix) + 6 # Assuming there's <100 mails per day (99.txt = 6 letters). If not, just pay to automate dude

            if (filename.startswith(filename_prefix) and 
                filename.endswith(".txt") and 
                len(filename) == expected_min_len):
                
                sequence_part = filename[len(filename_prefix) : len(filename_prefix) + 3]
                try:
                    current_sequence = int(sequence_part)
                    if current_sequence > max_sequence:
                        max_sequence = current_sequence
                except ValueError:
                    continue
    
    return max_sequence + 1


def extract_content_between_markers(text: str, start_marker: str, end_marker: str) -> str:
    """
    Extracts text content between the start and end markers.
    """
    start_index = text.find(start_marker)
    if start_index == -1:
        return text

    start_of_content = start_index + len(start_marker)

    end_index = text.find(end_marker, start_of_content)
    
    if end_index == -1:
        return text[start_of_content:].strip()
    
    return text[start_of_content:end_index].strip()


def fetch_emails(
    host: str,
    port: int,
    username: str,
    password: str,
    output_base_dir: str, 
    folder: str = 'INBOX',
    mark_as_read: bool = False,
    search_criteria: list = ['UNSEEN']
):
    saved_email_paths = []
    
    os.makedirs(output_base_dir, exist_ok=True)
    print(f"Ensured output directory '{output_base_dir}' exists.")

    ssl_context = ssl.create_default_context()

    try:
        with IMAPClient(host, port=port, ssl=True, ssl_context=ssl_context) as client:
            print(f"Connecting to {host}...")
            client.login(username, password)
            print("Logged in successfully.")

            client.select_folder(folder)
            print(f"Selected folder: '{folder}'")

            messages = client.search(search_criteria)
            print(f"Found {len(messages)} potential emails matching search criteria ('{' '.join(search_criteria)}').")

            if not messages:
                print("No new emails found matching the initial IMAP criteria.")
                return []

            response = client.fetch(messages, ['RFC822.HEADER', 'BODY[]', 'INTERNALDATE', 'FLAGS'])
            
            sorted_messages = sorted(response.items(), key=lambda item: item[1][b'INTERNALDATE'])


            for msg_id, data in sorted_messages:
                raw_email_bytes_full = data[b'BODY[]']
                raw_email_headers_bytes = data[b'RFC822.HEADER']
                
                msg_headers = BytesParser().parsebytes(raw_email_headers_bytes)

                subject = msg_headers.get('Subject', '').strip()
                from_header = msg_headers.get('From', '').strip()
                
                matched_sender_type = None
                for pattern, sender_type_prefix in EMAIL_SUBJECT_PATTERNS.items():
                    if re.match(pattern, subject):
                        matched_sender_type = sender_type_prefix
                        break
                
                if not matched_sender_type:
                    continue

                print(f"  Processing matched email {msg_id}: From='{from_header}', Subject='{subject}'")

                full_msg = BytesParser().parsebytes(raw_email_bytes_full)
                
                date_str = full_msg.get('Date')
                try:
                    email_date = datetime.strptime(date_str.split(' +')[0].strip(), '%a, %d %b %Y %H:%M:%S')
                except (ValueError, AttributeError):
                    email_date = datetime.now()
                
                date_for_filename = email_date.strftime('%Y%m%d')

                sequence_number = get_next_daily_sequence_from_files(output_base_dir, matched_sender_type, email_date)

                body_content = ''

                for part in full_msg.walk():
                    ctype = part.get_content_type()
                    cdisp = part.get('Content-Disposition')
                    
                    if cdisp is None or not cdisp.startswith('attachment'):
                        if ctype == 'text/plain':
                            try:
                                body_content = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8')
                                break 
                            except (UnicodeDecodeError, AttributeError):
                                body_content = part.get_payload(decode=True).decode('latin-1', errors='ignore')
                                break
                        elif ctype == 'text/html' and not body_content:
                            try:
                                body_content = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8')
                            except (UnicodeDecodeError, AttributeError):
                                body_content = part.get_payload(decode=True).decode('latin-1', errors='ignore')
                
                relevant_content = body_content
                if matched_sender_type in CONTENT_MARKERS:
                    start_m = CONTENT_MARKERS[matched_sender_type]["start"]
                    end_m = CONTENT_MARKERS[matched_sender_type]["end"]
                    relevant_content = extract_content_between_markers(body_content, start_m, end_m)
                    
                    if relevant_content == body_content:
                        print(f"  Warning: Markers not fully found for {matched_sender_type} email {msg_id}. Saving full body.")
                    else:
                        print(f"  Extracted content between markers for {matched_sender_type} email {msg_id}.")

                filename = f"{matched_sender_type}_{date_for_filename}_{sequence_number:03d}.txt" 
                file_path = os.path.join(output_base_dir, filename)

                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(f"Subject: {subject}\n")
                        f.write(f"Date: {date_str}\n\n")
                        f.write(relevant_content)
                    
                    print(f"  Saved email to: {file_path}")
                    saved_email_paths.append(file_path)

                    if mark_as_read:
                        client.set_flags(msg_id, ['\\Seen'])
                except IOError as e:
                    print(f"  Error saving file {file_path}: {e}")
                except Exception as e:
                    print(f"  An unexpected error occurred while processing email {msg_id}: {e}")


    except Exception as e:
        print(f"An error occurred during IMAP connection or email fetching: {e}")
    finally:
        print("IMAP client session closed.")

    return saved_email_paths

if __name__ == "__main__":
    load_dotenv()

    IMAP_HOST = os.getenv('EMAIL_HOST')
    IMAP_PORT = int(os.getenv('EMAIL_PORT', 993))
    IMAP_USER = os.getenv('EMAIL_USER')
    IMAP_PASS = os.getenv('EMAIL_PASS')
    EMAIL_OUTPUT_BASE_DIR = os.getenv('EMAIL_OUTPUT_BASE_DIR')

    if not all([IMAP_HOST, IMAP_USER, IMAP_PASS, EMAIL_OUTPUT_BASE_DIR]):
        print("Error: Please ensure EMAIL_HOST, EMAIL_USER, EMAIL_PASS, and EMAIL_OUTPUT_BASE_DIR are all set in your .env file.")
    else:
        print("\n--- Starting Filtered Email Fetching Process ---")
        processed_files = fetch_emails(
            host=IMAP_HOST,
            port=IMAP_PORT,
            username=IMAP_USER,
            password=IMAP_PASS,
            output_base_dir=EMAIL_OUTPUT_BASE_DIR,
            mark_as_read=True
        )

        if processed_files:
            print(f"\nSuccessfully processed and saved {len(processed_files)} matching email(s).")
            print("Saved files:")
            for path in processed_files:
                print(f"- {path}")
        else:
            print("No new matching emails were found or processed.")
