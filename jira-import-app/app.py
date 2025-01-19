import os
import time
import pandas as pd
from flask import Flask, request, render_template, url_for, send_file, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Define the upload folder
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def preprocess(data):
    """
    Processes the initial DataFrame by removing rows and columns based on
    pre-defined criteria, and adjusts the DataFrame to a suitable format
    for further processing.
    """
    # Remove the first row (the row with "As a user I need to"),
    # the 'C' columns (indicated by 'Unnamed: 3, 5, and 7'),
    # and keep only the first 6 columns
    if data.empty or data.shape[0] < 2:
        raise ValueError(
            "Input data is empty or doesn't have enough rows for processing."
        )

    data.drop(index=0, inplace=True, errors="ignore")
    for col_to_drop in ["Unnamed: 3", "Unnamed: 5", "Unnamed: 7"]:
        if col_to_drop in data.columns:
            data.drop(columns=[col_to_drop], inplace=True, errors="ignore")
    data = data.iloc[:, :6]

    # Remove empty rows
    data.dropna(how="all", inplace=True)

    # Reset the index after dropping rows
    data.reset_index(drop=True, inplace=True)

    # Ensure 'EPIC' column exists
    if "EPIC" not in data.columns:
        raise ValueError(
            "'EPIC' column not found in the input data. Ensure the input format is correct."
        )

    # Locate 'END' in the 'EPIC' column
    if "END" in data["EPIC"].values:
        end_index = data[data["EPIC"] == "END"].index[0]
        data = data[:end_index]
    else:
        raise ValueError(
            "The word 'END' is not found in the EPIC column. Ensure 'END' exists in your input data."
        )

    return data


def dataframeprocess(data):
    """
    Processes each row of the DataFrame to construct a structured format for JIRA issues bulk import
    purposes, separating Epics and Stories and calculating estimates.
    """

    # Expected columns: EPIC, SUMMARY, IOS, AND, SERV, NOTES
    required_cols = {"EPIC", "SUMMARY", "IOS", "AND", "SERV", "NOTES"}
    if not required_cols.issubset(data.columns):
        raise ValueError(
            f"Input data does not have the required columns: {required_cols}"
        )

    current_epic_name = ""
    epic_estimates = {}
    epic_components_tracker = {}
    columns = [
        "Issue Type",
        "Epic Name",
        "Epic Link",
        "Summary",
        "Description",
        "Components",
        "Original Estimate",
    ]
    final_data = pd.DataFrame(columns=columns)

    data_rows = []
    for index, row in data.iterrows():
        if pd.notna(row["EPIC"]):
            # This row is an Epic
            current_epic_name = row["EPIC"]
            epic_estimates[current_epic_name] = 0  # Initialize epic estimate
            epic_components_tracker[current_epic_name] = {
                "Android": False,
                "iOS": False,
                "Server": False,
            }
            data_rows.append(
                {
                    "Issue Type": "Epic",
                    "Epic Name": row["EPIC"],
                    "Epic Link": "",
                    "Summary": row["SUMMARY"],
                    "Description": row["NOTES"],
                    "Components": "",
                    "Original Estimate": "",
                }
            )
        elif pd.notna(row["SUMMARY"]):
            if not current_epic_name:
                raise ValueError(
                    f"Story row at index {index} does not have an associated Epic. Ensure all Stories follow an Epic in the CSV."
            )

            story_estimates = []
            # Server
            if pd.notna(row["SERV"]):
                epic_components_tracker[current_epic_name]["Server"] = True
                story_estimates.append(float(row["SERV"]))
                data_rows.append(
                    {
                        "Issue Type": "Story",
                        "Epic Name": "",
                        "Epic Link": current_epic_name,
                        "Summary": row["SUMMARY"],
                        "Description": row["NOTES"],
                        "Components": "Server",
                        "Original Estimate": row["SERV"],
                    }
                )
            # iOS
            if pd.notna(row["IOS"]):
                epic_components_tracker[current_epic_name]["iOS"] = True
                story_estimates.append(float(row["IOS"]))
                data_rows.append(
                    {
                        "Issue Type": "Story",
                        "Epic Name": "",
                        "Epic Link": current_epic_name,
                        "Summary": row["SUMMARY"],
                        "Description": row["NOTES"],
                        "Components": "iOS",
                        "Original Estimate": row["IOS"],
                    }
                )
            # Android
            if pd.notna(row["AND"]):
                epic_components_tracker[current_epic_name]["Android"] = True
                story_estimates.append(float(row["AND"]))
                data_rows.append(
                    {
                        "Issue Type": "Story",
                        "Epic Name": "",
                        "Epic Link": current_epic_name,
                        "Summary": row["SUMMARY"],
                        "Description": row["NOTES"],
                        "Components": "Android",
                        "Original Estimate": row["AND"],
                    }
                )

            # Add to epic estimate sum
            epic_estimates[current_epic_name] += sum(story_estimates)

    final_data = pd.concat([final_data, pd.DataFrame(data_rows)], ignore_index=True)
    return final_data, epic_estimates, epic_components_tracker


def postprocess(final_data, epic_estimates, epic_components_tracker):
    """
    Applies final transformations to the DataFrame, updating estimates,
    converting data types, and adjusting component values. 
    It also duplicates the components into two new columns.
    """
    # Update Epic estimates in final_data
    for index, row in final_data.iterrows():
        if row["Issue Type"] == "Epic" and row["Epic Name"] in epic_estimates:
            final_data.at[index, "Original Estimate"] = epic_estimates[row["Epic Name"]]

    # Convert all 'Original Estimate' values to float
    for idx in final_data.index:
        val = final_data.at[idx, "Original Estimate"]
        if val == "":
            val = 0
        final_data.at[idx, "Original Estimate"] = float(val)

    # Convert days to seconds (1 day = 8 hours, 1 hour = 3600 seconds)
    final_data["Original Estimate"] = final_data["Original Estimate"] * 8 * 3600

    # Round values
    final_data["Original Estimate"] = (
        final_data["Original Estimate"].round().astype(int)
    )

    # Add two new 'Components' columns
    final_data["Components 1"] = final_data["Components"]
    final_data["Components 2"] = final_data["Components"]

    # Update Components for Epics based on the tracker
    for index, row in final_data.iterrows():
        if row["Issue Type"] == "Epic":
            epic_name = row["Epic Name"]
            android = "Android" if epic_components_tracker[epic_name]["Android"] else ""
            ios = "iOS" if epic_components_tracker[epic_name]["iOS"] else ""
            server = "Server" if epic_components_tracker[epic_name]["Server"] else ""
            final_data.at[index, "Components"] = android
            final_data.at[index, "Components 1"] = ios
            final_data.at[index, "Components 2"] = server

    return final_data


def preprocess_file(input_filepath):
    """
    This function now performs the full specialized transformation
    rather than just adding a 'Processed' column.
    """
    # Load initial data
    data = pd.read_csv(input_filepath, header=0)

    # Run the specialized processing pipeline
    data = preprocess(data)
    final_data, epic_estimates, epic_components_tracker = dataframeprocess(data)
    final_data = postprocess(final_data, epic_estimates, epic_components_tracker)

    # Generate unique filename using timestamp
    timestamp = int(time.time())
    base_name = os.path.basename(input_filepath)
    name, ext = os.path.splitext(base_name)
    output_filename = f"{name}_{timestamp}_processed{ext}"
    output_filepath = os.path.join(os.path.dirname(input_filepath), output_filename)

    final_data.to_csv(output_filepath, index=False, encoding="utf-8-sig")
    return output_filepath


def upload_to_bucket(blob_name, file_path):
    """
    Simulate uploading by moving the file to a processed directory.
    """
    local_output_dir = os.path.join(app.config["UPLOAD_FOLDER"], "processed")
    os.makedirs(local_output_dir, exist_ok=True)  # Ensure directory exists
    output_path = os.path.join(local_output_dir, blob_name)
    os.rename(file_path, output_path)  # Move the file
    return output_path  # Return the correct full path


@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            return "No file part", 400
        file = request.files["file"]
        if file.filename == "":
            return "No selected file", 400

        upload_folder = app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)
        filename = secure_filename(file.filename)
        input_filepath = os.path.join(upload_folder, filename)
        file.save(input_filepath)

        # Process the file with the specialized transformations
        try:
            processed_file = preprocess_file(input_filepath)
        except ValueError as e:
            # Show error if there’s a formatting error(e.g., 'END' not found)
            return f"Error processing file: {e}", 400

        blob_name = os.path.basename(processed_file)
        upload_to_bucket(blob_name, processed_file)
        download_url = url_for("processed_file", filename=blob_name)
        return render_template("index.html", download_url=download_url)

    return render_template("index.html")


@app.route("/uploads/processed/<filename>")
def processed_file(filename):
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], "processed", filename)
    if not os.path.exists(file_path):
        abort(404, description="File not found")
    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    app.run(port=5001, debug=True)
