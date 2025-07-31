#Converts PDF to Docx Using Adobe SDKs
# Reference: https://developer.adobe.com/document-services/docs/overview/pdf-services-api/quickstarts/python/

import dotenv
import logging
import os
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

# Initial Setup and retieve credentials. 
credentials = ServicePrincipalCredentials(
    client_id=os.getenv('PDF_SERVICES_CLIENT_ID'),
    client_secret=os.getenv('PDF_SERVICES_CLIENT_SECRET')
)

# Create a services Instance. 
pdf_services=PDFServices(credentials=credentials)

# Filename Directory
user_input = input('What is the file name to be converted in the dndgpt_knowledge_base:')

# Add correct extension
if not user_input.endswith('.pdf'): 
    file_name_with_extension = user_input + '.pdf'

else: 
    file_name_with_extension = user_input

# Construct the full file path. 
base_dir = os.path.join("..","data","knowledge-base")
file_path = os.path.join(base_dir, file_name_with_extension)

# Retrieve the file. This is different than the suggestion based on ChatGPT input. Using a 'with' loop is superior to file.close() method because the with will close automatically. 
with open(file_path, 'rb') as file: 
    input_stream = file.read()

# Debugging: You can print the absolute file path to confirm it's correct.
print(f"Full file path: {os.path.abspath(file_path)}")

# Creates an asset(s) from source file(s) and upload
input_asset = pdf_services.upload(input_stream=input_stream, mime_type=PDFServicesMediaType.PDF)

# Creates parameters for the job
export_pdf_params = ExportPDFParams(target_format=ExportPDFTargetFormat.DOCX)

# Creates a new job instance. 
export_pdf_job = ExportPDFJob(input_asset=input_asset, export_pdf_params=export_pdf_params)

# Submit job and get result.
location = pdf_services.submit(export_pdf_job)
pdf_services_response = pdf_services.get_job_result(location, ExportPDFResult)

# Get content from the resulting asset(s)
result_asset: CloudAsset = pdf_services_response.get_result().get_asset()
stream_asset: StreamAsset = pdf_services.get_content(result_asset)

# Define output folder
output_folder = os.path.join("..", "data", "knowledge-base", "docx")

# Ensure output folder exists, or create it. 
if not os.path.exists(output_folder): 
    os.makedirs(output_folder)

# Define target format and extension, then the file path.     
target_format_with_extension = user_input + '.docx'

#creates an output stream and copy stream assets content to it. 
output_file_path = os.path.join(output_folder, target_format_with_extension) 
with open(output_file_path, "wb") as file: 
    file.write(stream_asset.get_input_stream())

# Optional: Print the file path to confirm the file is written
print(f"File successfully written to {output_file_path}")