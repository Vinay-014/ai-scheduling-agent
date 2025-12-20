#  AI-Powered Medical Appointment Scheduling Agent  

A streamlined **AI-driven scheduling system** designed to automate patient intake, appointment booking, reminders, and administrative reporting. Built with **Streamlit, Python, and workflow automation agents**, this project demonstrates an end-to-end healthcare scheduling solution with real-time email/SMS notifications.

![Demo](https://github.com/Vinay-014/ai-scheduling-agent/blob/main/Demo.gif)  


##  Features  

- **Patient Greeting & Intake** – Collects patient details (new/returning detection).  
- **Insurance Collection** – Stores carrier, member ID and group ID.  
- **Appointment Scheduling & Confirmation** – Generates appointment ID and sends confirmation via email.  
- **Form Handling** – Attaches patient intake form (PDF) to email.  
- **Reminder System** – Sends SMS/Email reminders at predefined intervals.  
- **Admin Reporting** – Generates Excel reports for admin review.  


##  Tech Stack  

- **Frontend/UI**: Streamlit  
- **Backend/Workflow**: Python  
- **Database**: CSV-based storage (patients, appointments, insurance)  
- **Email Service**: SMTP (Gmail App Password)  
- **SMS Service**: Simulated via `sms_utils`  
- **Libraries**: Pandas, UUID, Datetime, OpenPyXL  


##  Installation & Setup  

1. Clone the repository:  
   ```bash
   git clone https://github.com/your-username/ai-scheduling-agent.git
   cd ai-scheduling-agent

2. Install dependencies:
   ```bash
   pip install -r requirements.txt

3. Configure email credentials in utils/email_utils.py:
   ```bash
   EMAIL_ADDRESS = "your_email@gmail.com"
   EMAIL_PASSWORD = "your_app_specific_password"

4. Run the Streamlit app:
   ```bash
   streamlit run ui/app.py


##  Workflow Preview

Step 1 – Patient Greeting & Intake

Step 2 – Insurance Collection

Step 3 – Appointment Confirmation + PDF Email

Step 4 – Automated Reminders (Email + SMS)

Step 5 – Admin Reports

AI Scheduling Agent (MVP-1). Run python main.py for CLI workflow preview
