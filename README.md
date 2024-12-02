# Gmail API Project

This project extracts email data using the Gmail API and saves it into structured CSV files for analysis and storage.

## Features
- Fetches email metadata (e.g., sender, recipient, subject, date).
- Extracts email body content in plain text and HTML formats.
- Saves email attachments to a designated folder.
- Outputs email and attachment data to CSV files.

## Requirements
- Python 3.8 or higher
- Gmail API credentials (`credentials.json`)

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/seamus-linnane/gmail_fetch_api.git
cd share
```

### 2. Set Up Gmail API
```bash
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Enable the Gmail API for your project.
4. Create OAuth 2.0 credentials and download the `credentials.json` file.
5. Place the `credentials.json` file in the `share` directory.
6. If you already have a valid `token.json` file from a previous project:
   - Copy it into the `share` directory.
   - Ensure the file matches the Gmail account you want to use for this project.

   If you don’t have a `token.json` file:
   - Run the script once to generate it. You will be prompted to log in and authorize access.
```

### 3. Install Dependencies

Install the required Python libraries using pip:

```bash
pip install -r requirements.txt
```

### 4. Run the Script

Run the script to fetch emails and save the data:

```bash
python gmail_api.py
```

### 5. Outputs

- **Emails CSV**: `data/emails.csv` containing metadata and content for emails.
- **Attachments CSV**: `data/attachments.csv` (if attachments are present).

## File Structure

```
/share
  ├── data/                 # Folder for saved CSV files
  ├── attachments/          # Folder for saved attachments
  ├── gmail_api.py          # Main script
  ├── README.md             # Project documentation
  ├── requirements.txt      # Python dependencies
  ├── .gitignore            # Git ignore file
  ├── credentials.json      # Gmail API credentials (users own)
  ├── token.json            # Authentication token (users own)
```

## License

This project is licensed under the MIT License. See LICENSE for details.
