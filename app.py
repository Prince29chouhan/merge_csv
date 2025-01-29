from flask import Flask, request, render_template, send_file
import pandas as pd
import io
import tempfile
import os
from fuzzywuzzy import process, fuzz

app = Flask(__name__)

# Function to merge the dataframes based on a common column
def merge_data(df_list, common_column):
    # Start with the first dataframe
    merged_df = df_list[0]

    # Loop through the remaining dataframes and merge them
    for df in df_list[1:]:
        # Create a function to get the best match for a district name from df
        def get_best_match(district, choices):
            if isinstance(district, str):  # Check if the district is a string
                match, score = process.extractOne(district, choices, scorer=fuzz.ratio)
                return match if score >= 95 else district  # Return the original district name if no match is found
            return district  # Return the original district name if it's not a string

        # Get the unique district names from the current dataframe
        df_districts = df[common_column].dropna().unique()  # Drop NaN values

        # Apply the fuzzy matching function to the merged dataframe to get the best match from the current dataframe
        merged_df[common_column] = merged_df[common_column].apply(lambda x: get_best_match(x, df_districts))

        # Merge the dataframes on the updated district names
        merged_df = pd.merge(merged_df, df, left_on=common_column, right_on=common_column, how='left')

    return merged_df

# Route to handle file upload, merge, preview, and download
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Check if the request contains files and a common column
        if 'file1' not in request.files:
            return "No files uploaded", 400

        files = request.files.getlist('file1')  # Get all files uploaded under the name 'file1'
        common_column = request.form['common_column']
        merged_file_name = request.form.get('merged_file_name', 'merged_file')  # Get the name for the merged file, default to 'merged_file'

        if not files:
            return "No files selected", 400

        # Read the CSV files into dataframes
        df_list = []
        for file in files:
            if file.filename == '':
                return "No selected file", 400
            df = pd.read_csv(io.StringIO(file.stream.read().decode('utf-8')))
            df_list.append(df)

        # Perform the merge based on the common column
        try:
            merged_df = merge_data(df_list, common_column)
        except KeyError:
            return render_template('index.html', error_message="Common column not found in one or more files")

        # Preview the first 10 rows of the merged dataframe
        preview_df = merged_df.head(10)

        # Create a temporary directory using tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w', newline='') as tmp_file:
            merged_file_path = os.path.join(os.path.dirname(tmp_file.name), f"{merged_file_name}.csv")
            # Save the merged dataframe to the temporary file with the specified name
            merged_df.to_csv(merged_file_path, index=False)

        # Render the preview as an HTML table
        preview_html = preview_df.to_html(classes='table table-striped')

        return render_template('index.html', preview_html=preview_html, merged_file_path=merged_file_path)

    return render_template('index.html')

# Route to download the merged file
@app.route('/download')
def download_file():
    file_path = request.args.get('file')
    if file_path and os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "File not found", 404

if __name__ == '__main__':
    app.run(debug=True)
