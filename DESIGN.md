SteepItTogether Design

Our website is a python flask application. It utilizes Javascript, JQuery, CSS, and HTML, with Jinja for templating, for the front end, and python for the backend. Our database is a SQLite 3 in-memory database. We opted to use these technologies as they are flexible, lightweight, and they are amply documented. Additionally, we used the following python packages: 


<table>
  <tr>
   <td>Library
   </td>
   <td>What it does
   </td>
   <td>How we used it
   </td>
   <td>Why we chose it
   </td>
  </tr>
  <tr>
   <td>flask_mail
   </td>
   <td>Allows us to send emails to users
   </td>
   <td>We used it for account confirmation and password reset emails
   </td>
   <td>Integration with flask + with gmail (where we secured a custom email that matched our website domain)
   </td>
  </tr>
  <tr>
   <td>flask_moment
   </td>
   <td>Localized time and date 
   </td>
   <td>Pass appropriately localized time and date from the front end to the backend
   </td>
   <td>We could not use python to get the local browser time of our users, but we wanted to be able to store and display appropriate local times for journal entries
   </td>
  </tr>
  <tr>
   <td>itsdangerous
   </td>
   <td>Provides a way to cryptographically sign data in python
   </td>
   <td>Secure account confirmation and password reset with a secure, unique token (secured by SHA 1, which we learned on the test is a cryptographic hash)
   </td>
   <td>Flask integration and because we don’t want to have to store tokens in the database, meaning signed information can make a roundtrip between server and client
   </td>
  </tr>
</table>


Serving our application

Our application is running on an ubuntu instance in Amazon EC2. We are running it using a Linux command line script that invokes ‘nouhup’ to keep the process running. Additionally, we SSH into this remote machine to perform health checks and pull changes from GitHub. We purchased a domain name from GoDaddy and pointed the DNS servers to our Amazon EC2 instance’s public IP address.

Development tools

We utilized GitHub for version control since we were collaborating asynchronously on the website. 

Configuration

We configured our flask app with a local configuration file which we did not commit to GitHub for security reasons. In this file, we defined environmental variables including a secret key, our official email address, and our Gmail password. We configured our flask app to run on Port 5000 and to allow incoming traffic via the Amazon EC2 dashboard.

Photo Upload

Pass photo file as part of flask request, then save that file in our static photo directory. We store the file path to the photo in that directory in our database such that when we load the journal information, each entry as a data object includes a corresponding photo path, allowing the correct photo to be served. Additionally, we host 30 photos of buns in teacups which we serve randomly when the user does not provide a photo (these photos are served in a similar manner from this directory).

Email

We send our email using the email address and password configured as environmental variables in our local config file. We utilize SMTP as the protocol for sending mail to users from our configured Gmail account (steepittogether@gmail.com). We define an HTML template, a subject, and a recipient email address for each email. 