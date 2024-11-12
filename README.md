# us-visa-scheduler
The us-visa-scheduler is a bot for US VISA (usvisa-info.com) appointment rescheduling. This bot can help you reschedule your appointment to your desired time period. It supports rescheduling for multiple users.

## Prerequisites
- Having a US VISA appointment scheduled already.
- You are able to sign in to the page and check dates from the machine you are running this script. Sometimes access is blocked based on IP/region of original account login.

## Attention
- Right now, there are lots of unsupported embassies in our repository. A list of supported embassies is presented in the 'embassy.py' file.
- To add a new embassy (using English), you should find the embassy's "facility id." To do this, using google chrome, on the booking page of your account, right-click on the location section, then click "inspect." Then the right-hand window will be opened, highlighting the "select" item. You can find the "facility id" here and add this facility id in the 'embassy.py' file. There might be several facility ids for several different embassies. They can be added too. Please use the picture below as an illustration of the process.
![Finding Facility id](https://github.com/Soroosh-N/us_visa_scheduler/blob/main/_img.png?raw=true)

## Initial Setup
- Install Google Chrome [for install goto: https://www.google.com/chrome/]
- Install Python v3 [for install goto: https://www.python.org/downloads/]
- Install the required python packages:
```
python -m venv venv
source venv/bin/activate
pip install -r requirement.txt
```

## How to use
- Initial setup!
- Edit information [config.yaml.example file]. Then remove the ".example" from file name.
- Run visa.py file, using `python3 visa.py`
