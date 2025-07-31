#Converts the PDFs found in a directory into docx using the Adobe SDK. 
# Reference: https://developer.adobe.com/document-services/docs/overview/pdf-services-api/quickstarts/python/

import dotenv
import logging
import os
import sys
from datetime import datetime

from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
from adobe.pdfservices.operation.exception.exceptions import ServiceApiException, ServiceUsageException, SdkException
from adobe.pdfservices.operation.io.cloud_asset import CloudAsset
from adobe.pdfservices.operation.io.stream_asset import StreamAsset
from adobe.pdfservices.operation.pdf_services import PDFServices
from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
from adobe.pdfservices.operation.pdfjobs.jobs.export_pdf_job import ExportPDFJob
from adobe.pdfservices.operation.pdfjobs.params.export_pdf.export_pdf_params import ExportPDFParams
from adobe.pdfservices.operation.pdfjobs.params.export_pdf.export_pdf_target_format import ExportPDFTargetFormat
from adobe.pdfservices.operation.pdfjobs.result.export_pdf_result import ExportPDFResult

# Define the directory containing the PDFs
pdf_folder = os.path.join("..", "data", "knowledge-base")

# List all o fthe PDF files found in the directory. 
pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith('.pdf')]

# Count the number of files to convert.
files_remaining = len(pdf_files) 

# Display the files with some whitespace: 
print(f"\n\nPDF Files in {pdf_folder}:")
for pdf_file in pdf_files:
    print(pdf_file.ljust(25))
print(f"\nTotal Files to Convert: {files_remaining}")
print("\n") 

# Ask for user confirmation, cancel if "anything but yes or y"
confirmation = input("> Proceed with conversion? (y/n):").strip().lower()

if confirmation in ["yes", "y"]: 
    print("Proceeding with the conversion of the files...\n")
else: 
    print("Operation Cancelled...\n")
    sys.exit() #terminates the script. 

# Start error logging and handling
logging.basicConfig(filename='conversion_log.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - $(message)s')
logging.info("Starting PDF to DOCX conversion for multiple files.")

# Initial Setup and retieve credentials. 
credentials = ServicePrincipalCredentials(
    client_id=os.getenv('PDF_SERVICES_CLIENT_ID'),
    client_secret=os.getenv('PDF_SERVICES_CLIENT_SECRET')
)

# Create a services Instance. 
pdf_services=PDFServices(credentials=credentials)

# Process each file. 
for pdf_file in pdf_files: 
    try: 
        file_path = os.path.join(pdf_folder, pdf_file) 
        with open(file_path, 'rb') as file: 
            input_stream = file.read()
        
        # Debugging and logging the steps. 
        print(f"Processing file: {pdf_file}")
        logging.info(f"Processing file: {os.path.abspath(file_path)}")

        # Create an Asset(s) from the source file(s) and upload
        input_asset = pdf_services.upload(input_stream=input_stream, mime_type=PDFServicesMediaType.PDF)

        # Create paramters for the job.
        export_pdf_params = ExportPDFParams(target_format=ExportPDFTargetFormat.DOCX) 

        # Create a new job instance. 
        export_pdf_job = ExportPDFJob(input_asset=input_asset, export_pdf_params=export_pdf_params)

        # Submit job and get result. 
        location = pdf_services.submit(export_pdf_job)
        pdf_services_response = pdf_services.get_job_result(location, ExportPDFResult) 

        # Get the Content from the resulting asset: 
        result_asset: CloudAsset = pdf_services_response.get_result().get_asset()
        stream_asset: StreamAsset = pdf_services.get_content(result_asset) 

        # Define output file path, check to make sure the folder exists. 
        output_folder = os.path.join("..", "data", "knowledge-base", "docx") 
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Create correct extension for new file. 
        output_file_path = os.path.join(output_folder, pdf_file.replace('.pdf', '.docx'))

        # Print file to new path. 
        with open(output_file_path, "wb") as file: 
            file.write(stream_asset.get_input_stream())

        # Print success / falure, and log info. 
        print(f"File successfullly written to {output_file_path}\n")
        logging.info(f"Successfully converted {pdf_file} to DOCX.")

        # Print the total number of files remaining to process: 
        files_remaining -= 1 
        print(f"Files Remaining to Process: {files_remaining}\n")
    
    #Error Handling
    except (ServiceApiException, ServiceUsageException, SdkException) as e: 
        logging.error(f"Error processing {pdf_file}: {str(e)}")
        print(f"Failed to proces {pdf_file}, check the logs for details.") 