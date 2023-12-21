# CortexXDR-Data-Connector

Enhancing the security posture of your organization requires comprehensive visibility into your endpoint activities. Cortex XDR provides powerful threat detection and response capabilities, and integrating its logs with Azure Log Analytics can streamline your security operations. In this guide, we'll walk you through the process of creating a custom data connector using an Azure Function to fetch logs from Cortex XDR's API and store them in a custom table within your Log Analytics workspace.

# Prerequisites:
Before diving into the implementation, ensure you have the following in place:

1. Active Cortex XDR account with API url, access key ID and secret key.
2. Azure subscription with Log Analytics workspace provisioned.

# Installation / Setup Guide

1. Click "Deploy To Azure"
   <br />
   <br />
   [![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fpranjalv01%2FCortexXDR-Data-Connector%2Fmain%2Fazuredeploy.json)


3. Select the preferred Subscription, Resource Group and Location

4. Click on Review and deploy
5. Once the deployment succeeded, goto Configuration and provide below details:
   <br />
   a. WORKSPACE_ID = Azure Sentinel Workspace Id
   <br />
   b. SHARED_KEY = Azure Sentinel Shared Key
   <br />
   c. API_URL = Cortex XDR API Url
   <br />
   d. USER = Cortex XDR Access Key ID
   <br />
   e. PASSWORD = Cortex XDR Secret Key
   <br />

   Note: Replace with the orginal value.

6. Click on save.
7. You can see one custom table name "PaloAltoSentinel_CL" in your Log Analytics Workspace.

   

