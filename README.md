# JIRA Bulk Import CSV Processor

This project provides a web-based tool to preprocess CSV files for bulk import into JIRA. It structures the data, calculates estimates, and ensures compatibility with JIRA's issue tracking format. The application is built using Flask and pandas, with a responsive UI powered by Bootstrap.

## Features

CSV Uploads: Upload your raw CSV files through the web interface.
Data Processing:
Cleans unnecessary rows and columns.
Structures data into Epics and Stories for JIRA import.
Calculates and formats estimates and components.
Download Processed Files: Download structured CSV files ready for JIRA bulk import.

## Installation

Prerequisites
Python 3.9 or later
Docker (optional, for containerized deployment)

## Steps

Clone the repository:
git clone https://github.com/thabomtetwa/jira-bulk-import.git
cd jira-bulk-import
Set up a virtual environment and install dependencies:
python3 -m venv venv
source venv/bin/activate  # On Windows, use venv\Scripts\activate
pip install -r requirements.txt
Start the application:
python3 jira-import-app/app.py

## Usage

Open your browser and navigate to http://127.0.0.1:5000.
Upload your CSV file via the form on the homepage.
Download the processed file using the link provided after processing.

## Input Data Structure

For the application to process your CSV correctly, the input file must follow this format:

Required Columns:
Column Name	    Description
EPIC	        Defines the Epic names. Rows with a value in this column are treated as Epics.
SUMMARY	        Provides a brief description of the Epic or Story.
IOS	            Estimate (in days) for the iOS component of a Story.
AND	            Estimate (in days) for the Android component of a Story.
SERV	        Estimate (in days) for the Server component of a Story.
NOTES	        Additional notes or details for the Epic or Story.

Format Rules
1. Epics:
A row with a value in the EPIC column is treated as an Epic.
Subsequent rows without an EPIC value are considered Stories belonging to the most recent Epic.
2. Stories:
Rows with a SUMMARY value and estimates in the IOS, AND, or SERV columns are treated as Stories under the last defined Epic.
3. End Marker:
The EPIC column must include a row with the value END to signify the end of the data. Processing stops at this row.

Example Input (CSV):
EPIC,SUMMARY,IOS,AND,SERV,NOTES
Epic1,Epic 1 description,,,,"Notes for Epic1"
,Story 1 description,2,,,Notes for Story 1
,Story 2 description,,3,1,Notes for Story 2
Epic2,Epic 2 description,,,,"Notes for Epic2"
,Story 3 description,,1,2,Notes for Story 3
END,,,,,

## Example Workflow

1. Input CSV: Upload a file with columns such as EPIC, SUMMARY, IOS, AND, SERV, and NOTES.
2. Processing: The application:
    Removes unnecessary rows and columns.
    Structures data for JIRA.
    Calculates and formats estimates.
3. Output CSV: A structured file ready for JIRA bulk import.

## Technologies Used

Flask: Backend framework for building the web application.
pandas: Library for data manipulation and processing.
Bootstrap: Front-end framework for responsive design.

## Contributing

Contributions are welcome! To contribute:

Fork this repository.
Create a branch for your feature or bugfix.
Submit a pull request.

## Contact

Feel free to reach out via the GitHub repository for questions or feature requests.
