# Project part 1 (Cloud native ai agent)

-This ai agent application helps with automation of administrative tasks such as patient profile creation (during patient on boarding), editing of infomration of patient profile, checking of details in an online Electronic Medical Records System (Medplum).


How it works:

BEFORE: staffs of a clinic would need to converse with patients and then carry out all these administrative tasks on the EMR manually. (Eg. manually log in to systsem -> manually fill in patient details to create patient profile)

NOW: Patient directly converse with the ai agent via a chat interface , which the ai agent will then carry out the administrative task on the EMR instead of the clinic's staff


How to run this application? (there are 2 ways of doing so)

1. Run application locally on localhost:
  - 1. pip install -r requirements.txt
  - 2. in terminal run command "python browser_service.py" to start backend server running
  - 3. in seperate terminal run command "python -m streamlit run chatbot.py" or "streamlit run chatbot.py"

2. Run application locally via containers:
  - 1. In these 3 files, api_client.py, browser_service.py, chatbot.py. look for the comment which says/contains "to use if running application as container" and enable the line of code under it. Then disable the line of code under the comment which says/contains "o use if running appplication locally"

  - 2. run command "docker-compose up"

*NOTE when running application via containers:
-on local platform the agent works but the screenshot images will not work because the browser is trying to send request to backend using  http://backend which dont exist, but if u changed the env path to using localhost8000, now the agent will not work because the front end container will send request to itself with local host and since the front end container has nothing listening on port 8000 it fails

EXPECTED OUTPUT WHEN TESTING ON LOCAL.(using command : docker compose up):
- agent can work but cant see screenshot

BUT using this same codes in AWS with ALB it will work because ALB public url is reachable by the browser for images and reachable by front end contianer as well

IN AWS:
frontend image tags that work v4, v3
backend image tag that work v4, v2

in task definition for front end :need to specify environment to alb url, for back end : mount efs to container direcotry(efs id) 

