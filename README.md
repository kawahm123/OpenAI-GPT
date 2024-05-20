# Data Validation and Processing Flask Application
<h2>Description</h2>
This Flask application allows users to upload a CSV file, which is then processed to identify and report data integrity issues based on specific validation rules. The script validates the data by checking for unrealistic values, inconsistencies, missing information, and duplicates across various columns. After processing, the application generates an Excel file with multiple sheets, each containing records that violated one of the predefined validation rules, along with a Table of Contents for easy navigation. Users can then download the processed Excel file for further review and correction. The application employs OpenAI's GPT model to assist in data validation and provides a user-friendly web interface for uploading and downloading files.

# Real-Time FAQ Assistant Using OpenAI API
<h2>Description</h2>
This HTML page provides an interactive FAQ assistant that allows users to ask questions and receive real-time answers by leveraging the OpenAI API. When a user inputs a question and clicks the "Get Answer" button, the script fetches aggregated data from a specified JSON file. It then combines this data into a single text string, constructs a prompt, and sends it to the OpenAI API for processing. The response from the API is displayed as the answer to the user's question. The script also includes error handling to manage issues with data fetching and API responses.
