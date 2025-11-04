# AiAgent
-This is the script for creating an ai agent which take in input from user and create a patient profile for them in the self hosted medplum EMR

how to run?
1.pip install -r requirements.txt
2.in terminal run command "browser_service.py" to start backend running
3.in seperate terminal run command "python -m streamlit run chatbot.py" or "streamlit run chatbot.py"

NEW:
-on local dev platform (laptop) way to run this app is different. the images will not work because the browser is trying to send request to backend using  http://backend which dont exist, but if u changed the env path to using localhost8000, now the agent will not work because the front end container will send request to itself with local host and since the front end container has nothing listenbing on port 8000 it fails

BUT using this same codes in AWS with ALB it will work because ALB public url is reachable by the browser for images and reachable by front end contianer as well

IN AWS:
frontend image tags that work v4, v3
backend image tag that work v4, v2

in task definition for front end :need to specify environment to alb url, for back end : mount efs to container direcotry(efs id) 

EXPECTED OUTPUT WHEN TESTING ON LOCAL.(using command : docker compose up):
- agent can work but cant see screenshot