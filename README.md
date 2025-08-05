# imadeanrpa
a sample set of scripts from an RPA project I did for work that utilizes an AI browser automation tool to automate bookings.

This is a prime example of a jury-rigged dirt cheap solution that might work in lieu of a robust automation tool, and a budget, and the requisite man-hours.

A workflow is triggered by an incoming email, which triggers three processes sequentially:

- one that reads the email and determines if it's relevant, then extracts it
- one that takes the extracted mail and gets an AI to turn it into a prompt
- one that automates a desktop browser and pushes the prompt into the AI browser plugin, which then launches the booking website to complete the main task
