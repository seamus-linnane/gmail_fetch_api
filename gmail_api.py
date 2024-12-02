import os
import base64
import re
import html
import hashlib
from datetime import datetime
from email.utils import parseaddr
from dateutil import parser
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import logging

# Configure logging to output to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gmail_api.log'),
        logging.StreamHandler()  # This outputs to the console
    ]
)

# Constants
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
DATA_FOLDER = './data'
ATTACHMENTS_FOLDER = './attachments'
TOKEN_PATH = 'token.json'
CREDENTIALS_PATH = 'credentials.json'

def initialize_service():
    """Initializes the Gmail API service."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    else:
        if not os.path.exists(CREDENTIALS_PATH):
            logging.error("Missing credentials.json. Please provide it in the project directory.")
            raise FileNotFoundError("Missing credentials.json. Please provide it in the project directory.")
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
    return service

def decode_body(data):
    """Decodes the email body data."""
    if not data:
        return ""
    try:
        decoded_bytes = base64.urlsafe_b64decode(data)
        decoded_text = decoded_bytes.decode('UTF-8')
    except (base64.binascii.Error, UnicodeDecodeError):
        return ""
    decoded_text = html.unescape(decoded_text)
    decoded_text = re.sub(r'\r\n|\r|\n', '\n', decoded_text)  # Normalize line breaks
    decoded_text = re.sub(r'\n\s*\n', '\n\n', decoded_text)   # Remove excessive blank lines
    decoded_text = decoded_text.strip()                       # Remove leading/trailing whitespace
    decoded_text = re.sub(r' {2,}', ' ', decoded_text)        # Collapse multiple spaces
    decoded_text = re.sub(r'^\d+\s+', '', decoded_text)       # Remove leading numeric headers
    return decoded_text

def extract_text_from_parts(parts):
    """Recursively extracts text from email parts."""
    plain_text = ''
    for part in parts:
        mime_type = part.get('mimeType', '')
        body_data = ''
        if 'body' in part and 'data' in part['body']:
            body_data = decode_body(part['body']['data'])
        elif 'parts' in part:
            nested_text = extract_text_from_parts(part['parts'])
            plain_text += nested_text
            continue
        if mime_type == 'text/plain' and body_data:
            plain_text += body_data + '\n'
    return plain_text

def process_email(service, email_id):
    """Processes a single email and returns its data."""
    try:
        msg_data = service.users().messages().get(userId='me', id=email_id, format='full').execute()
    except Exception as e:
        logging.error(f"Error fetching email ID {email_id}: {e}")
        return None, None

    headers = msg_data.get('payload', {}).get('headers', [])
    header_dict = {header['name'].lower(): header['value'] for header in headers if 'name' in header and 'value' in header}

    email_data = {
        'email_id': msg_data['id'],
        'thread_id': msg_data.get('threadId', ''),
        'snippet': msg_data.get('snippet', ''),
        'label_ids': msg_data.get('labelIds', []),
        'from': header_dict.get('from', ''),
        'to': header_dict.get('to', ''),
        'cc': header_dict.get('cc', ''),
        'subject': header_dict.get('subject', ''),
        'date_received': parser.parse(header_dict.get('date', '')).isoformat() if header_dict.get('date', '') else None,
        'plain_text': ''
    }

    payload = msg_data.get('payload', {})
    if 'parts' in payload:
        plain_text = extract_text_from_parts(payload['parts'])
        email_data['plain_text'] = plain_text.strip()
    elif 'body' in payload and 'data' in payload['body']:
        email_data['plain_text'] = decode_body(payload['body']['data']).strip()

    attachments = []
    if 'parts' in payload:
        attachments = extract_attachments(payload['parts'], email_id)

    return email_data, attachments

def extract_attachments(parts, email_id):
    """Extracts attachments from email parts."""
    attachments = []
    for part in parts:
        filename = part.get('filename', '')
        body = part.get('body', {})
        if filename and 'attachmentId' in body:
            attachment_id = body['attachmentId']
            attachment_data = download_attachment(email_id, attachment_id)
            if attachment_data:
                save_attachment(filename, attachment_data)
                attachments.append({
                    'email_id': email_id,
                    'filename': filename,
                    'mime_type': part.get('mimeType', ''),
                    'size': body.get('size', 0)
                })
        elif 'parts' in part:
            attachments.extend(extract_attachments(part['parts'], email_id))
    return attachments

def download_attachment(email_id, attachment_id):
    """Downloads an attachment using the Gmail API."""
    try:
        attachment = service.users().messages().attachments().get(
            userId='me',
            messageId=email_id,
            id=attachment_id
        ).execute()
        data = attachment.get('data', '')
        return base64.urlsafe_b64decode(data.encode('UTF-8'))
    except Exception as e:
        logging.error(f"Error downloading attachment {attachment_id} from email {email_id}: {e}")
        return None

def save_attachment(filename, data):
    """Saves the attachment to the attachments folder."""
    if not os.path.exists(ATTACHMENTS_FOLDER):
        os.makedirs(ATTACHMENTS_FOLDER)
    filepath = os.path.join(ATTACHMENTS_FOLDER, filename)
    try:
        with open(filepath, 'wb') as f:
            f.write(data)
        logging.info(f"Saved attachment: {filename}")
    except Exception as e:
        logging.error(f"Error saving attachment {filename}: {e}")

def main():
    """Main function to execute the script."""
    global service
    service = initialize_service()

    # Ensure directories exist
    os.makedirs(DATA_FOLDER, exist_ok=True)
    os.makedirs(ATTACHMENTS_FOLDER, exist_ok=True)

    # Fetch the list of email IDs
    try:
        response = service.users().messages().list(userId='me', maxResults=10).execute()
        email_ids = [email['id'] for email in response.get('messages', [])]
    except Exception as e:
        logging.error(f"Error fetching email list: {e}")
        return

    emails_data = []
    all_attachments = []

    for email_id in email_ids:
        logging.info(f"Processing email ID: {email_id}")
        email_data, attachments = process_email(service, email_id)
        if email_data:
            emails_data.append(email_data)
        if attachments:
            all_attachments.extend(attachments)

    # Create DataFrames
    emails_df = pd.DataFrame(emails_data)
    attachments_df = pd.DataFrame(all_attachments)

    # Save to CSV
    emails_csv_path = os.path.join(DATA_FOLDER, 'emails.csv')
    attachments_csv_path = os.path.join(DATA_FOLDER, 'attachments.csv')

    emails_df.to_csv(emails_csv_path, index=False, encoding='utf-8')
    logging.info(f"Emails data saved to {emails_csv_path}")

    if not attachments_df.empty:
        attachments_df.to_csv(attachments_csv_path, index=False)
        logging.info(f"Attachments data saved to {attachments_csv_path}")
    else:
        logging.info("No attachments found.")

if __name__ == '__main__':
    main()