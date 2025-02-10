import requests
import json
import os
from datetime import datetime
import time
from openpyxl import Workbook

# Initialize variables
page = 1
all_data = []
TOKEN = os.getenv('TOKEN')
PER_PAGE = os.getenv('PER_PAGE')
SPRINT_START_DATE = os.getenv('SPRINT_START_DATE')

# Fetch merge requests with pagination
while True:
    response = requests.get(
        f"https://gitlab.cloud/api/v4/groups/5591/merge_requests",
        headers={"Private-Token": TOKEN},
        params={
            "state": "all",
            "scope": "all",
            "per_page": PER_PAGE,
            "created_after": SPRINT_START_DATE,
            "page": page
        }
    )
    data = response.json()
    
    if not data:
        break
    
    all_data.extend(data)
    page += 1

# Save all data to a file
with open('i.json', 'w') as f:
    json.dump(all_data, f, indent=4)

# Extract IDs
f_ids = [mr['iid'] for mr in all_data]
v_ids = [mr['project_id'] for mr in all_data]

# Generate filename
fname = datetime.now().strftime("%Y_%m_%d_%I_%M_%p")

# Loop through pages and IDs
page = 1
while True:
    fetched_any = False
    for f_id, v_id in zip(f_ids, v_ids):
        item = f"https://gitlab.cloud/api/v4/projects/{v_id}/merge_requests/{f_id}/discussions.json"
        response = requests.get(
            item,
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Cookie": "preferred_language=en"
            },
            params={"per_page": PER_PAGE, "page": page}
        )
        data = response.json()
        
        if not data:
            continue
        
        fetched_any = True
        with open(f'./{fname}-{page}.json', 'a') as f:
            json.dump(data, f, indent=4)
            f.write("\n=============\n")
        
        time.sleep(2)
    
    if not fetched_any:
        break
    
    page += 1

# Clean up the JSON file to ensure proper format and store in mrdata.json
cleaned_discussions = []
for i in range(1, page):
    with open(f'./{fname}-{i}.json', 'r') as f:
        content = f.read()
    
    cleaned_content = content.replace("}\n]\n=============\n[\n    {", "},\n    {")
    cleaned_content = cleaned_content.replace("]\n=============\n", "]")
    
    cleaned_discussions.extend(json.loads(cleaned_content))

with open('mrdata.json', 'w') as f:
    json.dump(cleaned_discussions, f, indent=4)

print("Script executed and JSON files cleaned up successfully. Final data stored in mrdata.json.")

# Reviewer mapping
reviewer_mapping = [
  {"Lastname, Firstname (Gitlab_Username)": ["Team","RM","L3"]},
  {"Lastname, Firstname (Gitlab_Username)": ["Team","TL","L2"]},
  {"Lastname, Firstname (Gitlab_Username)": ["Team","SD","L1"]}
]

# Load the JSON data
with open('mrdata.json', 'r') as file:
    data = json.load(file)

# Create an Excel workbook and sheet
wb = Workbook()
ws = wb.active
ws.title = "MR Stats"

# Define headers
headers = ["Sprint", "POD", "Role", "Reviewer", "Pod Member", "MR", "Comments", "Category", "Within Checklist"]
ws.append(headers)

# Get the sprint name and file name from environment variables
sprint = os.getenv('SPRINT_NAME', 'SPRINT 2')
file_name = os.getenv('FILE_NAME', 'PI5SP3-MR-stats-v1.xlsx')

# Populate the Excel sheet with data
for item in data:
    notes = item.get("notes", [])
    for note in filter(lambda n: n.get("type") == "DiffNote", notes):
        author = note.get('author', {}).get('name')
        created = note.get('created')
        mr_id = f"{note.get('project_id')}-{note.get('noteable_iid')}"
        comment = note.get('body', '').replace(',', ' ')
        category = "TBD"
        within_checklist = "TBD"
        if "changed this line" in comment:
            continue
        reviewer = next((r for r in reviewer_mapping if author in r), None)
        if reviewer is None:
            ws.append([sprint, "TBD", "TBD", "TBD", author, mr_id, comment, category, within_checklist])
        else:
            userdata = list(reviewer.values())[0]
            ws.append([sprint, *userdata, author, mr_id, comment, category, within_checklist])

# Save the Excel file
wb.save(file_name)

print("Excel file generated successfully.")
