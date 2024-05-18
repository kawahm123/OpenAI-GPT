import os
from flask import Flask, request, redirect, url_for, send_file, render_template_string
import pandas as pd
from datetime import date
import openai
from werkzeug.utils import secure_filename

# Set your OpenAI API key here
openai.api_key = 'your-openai-api-key'  # Replace with your actual OpenAI API key

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROCESSED_FOLDER'] = 'processed'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

# Function to process a chunk of data using OpenAI's GPT model
def process_chunk(chunk):
    try:
        # Request GPT to validate the given data chunk
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a data validation assistant."},
                {"role": "user", "content": f"Validate the following data chunk: {chunk.to_dict()}"}
            ]
        )
        suggestions = response.choices[0].message['content'].strip()
        return suggestions
    except Exception as e:
        print(f"Error processing chunk: {e}")
        return ""

# Function to process the uploaded CSV file and conduct data validations
def process_file(file_path):
    df = pd.read_csv(file_path)  # Read the CSV file into a DataFrame

    flagged_urls = set()  # Set to track already flagged URLs

    validation_results = []  # List to store validation results

    # Function to apply validation rules and track flagged URLs
    def validate_and_flag(rule_number, condition):
        nonlocal flagged_urls
        validation_result = df[condition]
        new_flags = set(validation_result['url']) - flagged_urls
        validation_result = validation_result[validation_result['url'].isin(new_flags)]
        flagged_urls.update(new_flags)
        validation_results.append((rule_number, validation_result))

    # Apply various validation rules
    validate_and_flag("1. Value Over Limit", (df['min_value'] > 150) | (df['max_value'] > 150))
    validate_and_flag("2. Available > Size", df['available'] > df['size'])
    validate_and_flag("3. Type Null", df['type'].isna())
    validate_and_flag("4. Type Not Specified Null Addr", (df['type'] != 'SPECIFIED') & df['address'].isna())
    validate_and_flag("5. Size 0 or Null", (df['size'].isna()) | (df['size'] == 0))
    validate_and_flag("6. Size 0 or Null Type Not Specified", (df['size'].isna() | (df['size'] == 0)) & (df['type'] != 'SPECIFIED'))
    validate_and_flag("7. Duplicate Records", df.duplicated(subset=['available', 'suite', 'address'], keep=False))
    df['listing_levels_numeric'] = pd.to_numeric(df['listing_levels'], errors='coerce')
    validate_and_flag("8. Levels Mismatch", df['listing_levels_numeric'] > df['builtout_levels'])
    validate_and_flag("9. Type Mismatch", (df['type'] != 'SPECIFIED') & (df['category'] == 'SPECIFIED'))
    validate_and_flag("10. Condo Status Mismatch 1", ((df['condo_status_1'] == 'N') | df['condo_status_1'].isna()) & (df['condo_status_2'] == 'Y'))
    validate_and_flag("11. Condo Status Mismatch 2", ((df['condo_status_2'] == 'N') | df['condo_status_2'].isna()) & (df['condo_status_1'] == 'Y'))

    # Descriptions of the validation results
    descriptions = [
        "Original Data: The original dataset provided.",
        "1. Value Over Limit: Records where either min_value or max_value are over 150.",
        "2. Available > Size: Records where available is greater than size.",
        "3. Type Null: Records where type column has NULL values.",
        "4. Type Not Specified Null Addr: Records where type column is not 'SPECIFIED' and address column is NULL.",
        "5. Size 0 or Null: Records where size column includes '0' or NULL values.",
        "6. Size 0 or Null Type Not Specified: Records where size column includes '0' or NULL values and type column is not 'SPECIFIED'.",
        "7. Duplicate Records: Records where there are duplicate values in the available and suite columns with the same address.",
        "8. Levels Mismatch: Records where listing_levels is greater than builtout_levels.",
        "9. Type Mismatch: Records where type column is not 'SPECIFIED' but ‘category’ column is ‘SPECIFIED’.",
        "10. Condo Status Mismatch 1: Records where condo_status_1 column is 'N' or Null and condo_status_2 column is 'Y'.",
        "11. Condo Status Mismatch 2: Records where condo_status_2 column is 'N' or Null and condo_status_1 column is 'Y'."
    ]

    # Dictionary to store DataFrames with validation results
    dfs = {
        'Original Data': df,
    }
    dfs.update({desc.split(":")[0]: result for desc, (rule_number, result) in zip(descriptions[1:], validation_results)})

    # Define the output file path
    output_file = os.path.join(app.config['PROCESSED_FOLDER'], f'validated_data_{date.today()}.xlsx')

    # Write validation results to an Excel file with multiple sheets
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('Table of Contents')
        worksheet.write('A1', 'Table of Contents')

        # Add descriptions to the Table of Contents
        row = 2
        for description in descriptions:
            sheet_name, desc = description.split(':', 1)
            sheet_name = sheet_name.strip()
            desc = desc.strip()

            worksheet.write(row, 0, sheet_name)
            worksheet.write(row, 1, desc)
            worksheet.write_url(row, 2, f"internal:'{sheet_name}'!A1", string='Go to Sheet')
            row += 1

        # Write each DataFrame to a separate sheet in the Excel file
        for sheet_name, dataframe in dfs.items():
            dataframe.to_excel(writer, index=False, sheet_name=sheet_name)

    return output_file

# Route to handle file upload and processing
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return "No file part"
        file = request.files['file']
        if file.filename == '':
            return "No selected file"
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        processed_file = process_file(file_path)
        return redirect(url_for('download_file', filename=os.path.basename(processed_file)))
    return render_template_string('''
        <!doctype html>
        <title>Upload CSV File</title>
        <h1>Upload CSV File</h1>
        <form method=post enctype=multipart/form-data>
          <input type=file name=file>
          <input type=submit value=Upload>
        </form>
    ''')

# Route to serve the processed file for download
@app.route('/uploads/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=8080)