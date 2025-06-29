import os
import csv
from pathlib import Path

def extract_image_names_to_csv():
    """
    Extract image names from ai_overview_screenshots folder,
    remove '_ai_overview.png' suffix, and save to CSV file.
    """
    # Define the folder path
    folder_path = r"C:\Users\Admin\PycharmProjects\google_ai_overview\ai_overview_screenshots"
    
    # Output CSV file path
    output_csv = "image_names.csv"
    
    # List to store cleaned image names
    image_names = []
    
    try:
        # Check if folder exists
        if not os.path.exists(folder_path):
            print(f"Error: Folder '{folder_path}' does not exist.")
            return
        
        # Get all files in the directory
        files = os.listdir(folder_path)
        
        # Filter for PNG files ending with '_ai_overview.png'
        for file in files:
            if file.endswith('_ai_overview.png'):
                # Remove the '_ai_overview.png' suffix and replace underscores with spaces
                clean_name = file.replace('_ai_overview.png', '').replace('_', ' ')
                image_names.append(clean_name)
                print(f"Processed: {file} -> {clean_name}")
        
        # Sort the names alphabetically
        image_names.sort()
        
        # Write to CSV file
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['Image Name'])
            
            # Write each image name as a row
            for name in image_names:
                writer.writerow([name])
        
        print(f"\nSuccess! Extracted {len(image_names)} image names to '{output_csv}'")
        print(f"Image names saved:")
        for name in image_names:
            print(f"  - {name}")
            
    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    extract_image_names_to_csv()