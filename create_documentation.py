import os
import subprocess
from pathlib import Path

# Set paths
repo_path = "/Users/eldar/ivt/llm-pipeline"  # Path to the local GitHub repo
output_file = "documentation.docx"  # Change to .pdf for PDF output
docs_folder = os.path.join(repo_path, "docs")
combined_md = "combined.md"  # Temporary file to hold combined markdown


# Function to collect Markdown files and combine them
def collect_and_combine_markdown(base_path, output_path):
    md_files = []
    for root, _, files in os.walk(base_path):
        for file in sorted(files):  # Sorting ensures predictable order
            if file.endswith(".md"):
                md_files.append(os.path.join(root, file))

    with open(output_path, "w", encoding="utf-8") as outfile:
        for md_file in md_files:
            with open(md_file, "r", encoding="utf-8") as infile:
                outfile.write(infile.read() + "\n\n")
    print(f"Combined Markdown saved to {output_path}")


# Function to convert Markdown to DOCX or PDF
def convert_to_docx_or_pdf(md_file, output_file):
    try:
        subprocess.run(["pandoc", md_file, "-o", output_file], check=True)
        print(f"Converted {md_file} to {output_file}")
    except subprocess.CalledProcessError as e:
        print("Error during conversion:", e)


# Main execution
if __name__ == "__main__":
    # Combine all Markdown files
    collect_and_combine_markdown(docs_folder, combined_md)

    # Convert to DOCX or PDF
    convert_to_docx_or_pdf(combined_md, output_file)

    # Cleanup (optional)
    os.remove(combined_md)
